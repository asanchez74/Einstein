# Exploitation et sauvegarde de Pi-hole

## Configuration versionnée

La stack `compose/pihole/` utilise un volume persistant pour `/etc/pihole`.
`DATA_DIR` est partagé entre Compose et `backup-stack.sh` pour que le répertoire
archivé corresponde au volume utilisé. Sa valeur par défaut est
`/volume1/docker/einstein/data/pihole`.

Pour un `.env` NAS créé avant l'ajout de cette variable, ajouter explicitement :

```dotenv
DATA_DIR=/volume1/docker/einstein/data/pihole
```

Si le service utilise déjà un autre chemin, conserver ce chemin. Un changement
de `DATA_DIR` ne déplace pas les données ; vérifier le volume avant tout
redéploiement. La valeur par défaut Compose conserve le montage existant tant
que la variable n'est pas renseignée, mais le script de sauvegarde exige sa
présence explicite dans le `.env`.

Les paramètres réseau de référence sont :

| Élément | Valeur |
|---|---|
| Pi-hole LAN (macvlan) | `192.168.1.56` |
| Interface parente | `ovs_bond0`, à vérifier sur le NAS |
| Pi-hole VPN (bridge) | `172.23.0.2` |
| Réseau bridge VPN | `172.23.0.0/24` |
| DNS amont | FRITZ!Box `192.168.1.1`, secours Quad9 `9.9.9.9` (`strict-order`) |

Le fichier Compose définit les réseaux ; il ne configure pas le routage
OpenVPN, les règles DSM ou la distribution DNS aux clients. Ces réglages
externes doivent être conservés séparément.

## DNS amont et secours

Pi-hole interroge la FRITZ!Box `192.168.1.1`, qui transmet à Quad9 en
DNS-over-TLS. Quad9 direct `9.9.9.9` est déclaré en second via
`UPSTREAM_DNS="192.168.1.1;9.9.9.9"` dans le `.env` runtime, et l'option
dnsmasq `strict-order` est ajoutée par `FTLCONF_misc_dnsmasq_lines`.

Sans `strict-order`, dnsmasq privilégie le serveur le plus rapide et
interroge régulièrement tous les serveurs : `9.9.9.9` recevrait une partie
du trafic en temps normal, en clair et hors du DoT de la FRITZ!Box. Avec
`strict-order`, chaque requête part vers la FRITZ!Box ; Quad9 direct n'est
utilisé que si elle échoue.

Comportement vérifié le 24 octobre 2026 dans le dnsmasq intégré à Pi-hole
FTL (`src/dnsmasq/forward.c`, branche `master`) : `reply_query()` renvoie la
requête au serveur suivant lorsque la réponse est `SERVFAIL` ou `REFUSED` et
que `forwardall` vaut 0, ce qui est le cas en `strict-order` sans
`all-servers`. Si la FRITZ!Box ne répond plus du tout, la bascule intervient
à la nouvelle tentative du client, après son propre délai (une à quelques
secondes). Le basculement n'a pas été provoqué sur le réseau réel.

En secours, les requêtes vers `9.9.9.9` ne sont pas chiffrées entre le NAS
et Quad9. Le filtrage des domaines malveillants de Quad9 est conservé.

### Incident du 24 octobre 2026

De 09:27 à 11:20, la FRITZ!Box a répondu `SERVFAIL` à toutes les requêtes :
sa liaison DNS-over-TLS vers Quad9 était tombée et aucun serveur de repli
n'était configuré. Pi-hole n'ayant qu'un amont, la résolution était
indisponible sur le LAN et le VPN. Correctifs : second serveur DoT ajouté
côté FRITZ!Box par le propriétaire ; côté Pi-hole, Quad9 direct en secours
avec `strict-order`, qui aurait rejoué chaque `SERVFAIL` vers `9.9.9.9`.

### Déploiement et contrôle

Dans `compose/pihole/.env` sur le NAS, remplacer la ligne `UPSTREAM_DNS` :

```dotenv
UPSTREAM_DNS="192.168.1.1;9.9.9.9"
```

Après `git pull --ff-only`, redéployer avec `sudo scripts/stack-up.sh pihole`
(courte interruption DNS), puis vérifier :

```bash
sudo /usr/local/bin/docker exec pihole pihole-FTL --config dns.upstreams
sudo /usr/local/bin/docker exec pihole grep -x strict-order /etc/pihole/dnsmasq.conf
nslookup example.org 192.168.1.56
```

Dans le journal des requêtes Pi-hole, les réponses doivent être transmises à
`192.168.1.1#53` en fonctionnement normal.

## Ressources

Pi-hole utilise une limite mémoire de 512 Mio et `cpu_shares: 2048`.
Le propriétaire a choisi de conserver la pondération présente sur le NAS
pour aligner le dépôt avec le déploiement. Cette valeur donne un poids
relatif plus élevé que les services configurés à 256 lorsque le processeur
est disputé ; elle ne réserve pas de CPU et ne constitue pas un plafond.
Voir l'[ADR-0004](adr/0004-gestion-ressources-cpu-dsm.md).

## Noms DNS locaux

`router` et `router.chantevigne.com` pointent vers `192.168.1.2`, adresse du
routeur Synology RT2600ac confirmée par le propriétaire. Le NAS conserve
l'adresse `192.168.1.3` et la FRITZ!Box `192.168.1.1`.

Après déploiement, vérifier depuis un client LAN puis VPN :

```bash
nslookup router.chantevigne.com 192.168.1.56
```

La réponse attendue est `192.168.1.2`. Depuis le VPN, utiliser l'adresse DNS
Pi-hole effectivement distribuée au client si elle diffère de l'adresse LAN.
Ce contrôle reste à effectuer sur le réseau réel.

## Sauvegarder les données

Le script arrête temporairement Pi-hole. Prévoir une fenêtre d'interruption
DNS et conserver un accès au NAS par adresse IP.

Depuis le clone NAS, préparer une destination réservée à root :

```bash
sudo install -d -o root -g root -m 0700 /volume1/docker/einstein/backups/pihole
cd ~/Development/Einstein
sudo ./scripts/backup-stack.sh pihole
./scripts/stack-status.sh pihole
./scripts/stack-logs.sh pihole --tail 50
```

Le script produit une archive `.tar.gz` et un manifeste `.tar.gz.txt` contenant
l'empreinte SHA-256 et le commit Git. Vérifier son code de sortie, puis comparer
l'empreinte calculée avec celle du manifeste et examiner la liste des fichiers :

```bash
# Remplacer par le chemin exact affiché par le script.
ARCHIVE=/volume1/docker/einstein/backups/pihole/pihole-AAAAMMJJ-HHMMSS.tar.gz
sudo sha256sum "$ARCHIVE"
sudo cat "${ARCHIVE}.txt"
sudo tar -tzf "$ARCHIVE"
```

L'archive couvre `/etc/pihole`, y compris le fichier généré
`synology-hosts.list`. Les baux DHCP Synology sources restent hors de ce volume.
Les archives peuvent contenir des configurations et historiques DNS privés.

## Éléments à conserver séparément

- `compose/pihole/.env` réel, avec accès restreint ;
- `/volume1/docker/einstein/secrets/pihole_webpasswd.txt`, hors de l'archive de données ;
- configuration DHCP Synology et éventuelle tâche planifiée de synchronisation ;
- règles DSM, routage OpenVPN et configuration DNS distribuée aux clients ;
- commit Git correspondant au déploiement et manifeste de sauvegarde.

Conserver ces éléments dans une sauvegarde privée avec des permissions
restrictives. Ne pas les ajouter au dépôt. Une copie sur le même NAS ne couvre
pas la perte de l'hôte ; prévoir une copie externe privée selon la politique
de sauvegarde retenue.

## Restauration à valider sur le NAS

1. Vérifier le manifeste, l'empreinte et le contenu de l'archive.
2. Arrêter la stack et préserver les données actuelles avant remplacement.
3. Extraire dans un répertoire de préparation, contrôler le dossier archivé,
   les propriétaires et permissions, puis remettre les données dans `DATA_DIR`.
4. Restaurer séparément le `.env`, le secret et les réglages DSM/réseau nécessaires.
5. Utiliser le commit correspondant et redémarrer avec `stack-up.sh pihole`.
6. Contrôler les logs, l'interface d'administration et les réponses DNS depuis
   un client LAN puis VPN, notamment les noms locaux et un domaine externe.

Le script de sauvegarde ne fournit pas de restauration automatisée. Cette
procédure reste à exécuter et à consigner sur le NAS ; aucune restauration
Pi-hole n'est déclarée validée par cette documentation.

## Synchronisation des noms DHCP

`scripts/sync-synology-dhcp-to-pihole.sh` lit les baux Synology et génère
`/volume1/docker/einstein/data/pihole/synology-hosts.list`, puis recharge FTL
si le conteneur existe. Son exécution nécessite root.

Si `DATA_DIR` est personnalisé, fournir `OUTPUT_FILE` vers le fichier
`synology-hosts.list` de ce répertoire. Le script conserve le fichier existant
si aucun bail exploitable n'est trouvé. Il ne crée pas de tâche planifiée :
la fréquence et la configuration éventuelle dans DSM restent à vérifier et
à documenter sur le NAS. Éviter une synchronisation concurrente pendant la
sauvegarde ou la restauration.
