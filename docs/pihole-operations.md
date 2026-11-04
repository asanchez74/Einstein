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

Effet de bord attendu : un domaine réellement cassé (signature DNSSEC
invalide, serveurs de noms du domaine en panne) obtient aussi `SERVFAIL` de
la FRITZ!Box ; Pi-hole rejoue alors la requête en clair vers `9.9.9.9`, qui
répond généralement `SERVFAIL` à son tour. Ces requêtes, rares, apparaissent
vers `9.9.9.9` dans les statistiques de Pi-hole : ce n'est pas une anomalie.
Un volume important ou durable vers `9.9.9.9` signale en revanche un
problème côté FRITZ!Box.

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
# NAS
sudo /usr/local/bin/docker exec pihole pihole-FTL --config dns.upstreams
sudo /usr/local/bin/docker exec pihole grep -x strict-order /etc/pihole/dnsmasq.conf
```

La résolution se contrôle depuis un client du LAN, pas depuis le NAS : en
mode macvlan, l'hôte ne peut pas joindre ses propres conteneurs, et un
`nslookup` lancé sur le NAS vers `192.168.1.56` expire toujours. Attendre
aussi la fin du démarrage (`healthy`).

```bash
# Mac sur le LAN
nslookup example.org 192.168.1.56
nslookup nas.chantevigne.com 192.168.1.56
```

Dans le journal des requêtes Pi-hole, les réponses doivent être transmises à
`192.168.1.1#53` en fonctionnement normal.

Déployé le 24 octobre 2026 au commit `7224aec` : `dns.upstreams` vaut
`[ 192.168.1.1, 9.9.9.9 ]`, `strict-order` est présent dans
`/etc/pihole/dnsmasq.conf`, et le Mac résout `example.org` ainsi que
`nas.chantevigne.com` (`192.168.1.3`) via `192.168.1.56`.

### Test facultatif du basculement

Le cas « FRITZ!Box muette » se simule avec `192.0.2.1`, adresse réservée à
la documentation (RFC 5737) qui ne répond jamais. Interruption DNS brève.

```bash
# NAS : premier amont muet
cd ~/Development/Einstein/compose/pihole
sed -i 's|^UPSTREAM_DNS=.*$|UPSTREAM_DNS="192.0.2.1;9.9.9.9"|' .env
cd ../.. && sudo scripts/stack-up.sh pihole
```

```bash
# Mac, une fois Pi-hole healthy : réponse attendue après un court délai
nslookup example.org 192.168.1.56
```

```bash
# NAS : retour à la configuration normale
cd ~/Development/Einstein/compose/pihole
sed -i 's|^UPSTREAM_DNS=.*$|UPSTREAM_DNS="192.168.1.1;9.9.9.9"|' .env
cd ../.. && sudo scripts/stack-up.sh pihole
```

Le cas `SERVFAIL` de l'incident est plus difficile à reproduire ; il repose
sur la lecture du code FTL ci-dessus.

## Noms locaux introuvables (corrigé le 1er novembre 2026)

**Cause.** Jusqu'au 1er novembre 2026, le DHCP distribuait Pi-hole
`192.168.1.56`, puis la FRITZ!Box `192.168.1.1` comme DNS secondaire
(constaté sur le Mac avec `scutil --dns`). La FRITZ!Box maintenait la
résolution si le conteneur Pi-hole s'arrêtait, mais ne connaît pas les noms
locaux définis dans Pi-hole :

```text
$ nslookup pi-hole.chantevigne.com 192.168.1.1
** server can't find pi-hole.chantevigne.com: NXDOMAIN
```

Lorsque macOS interrogeait le serveur secondaire, un nom local
(`pi-hole`, `einstein`, `nas`, `router.chantevigne.com`) pouvait devenir
introuvable quelques minutes, le temps que la réponse négative expire.
Observé le 25 octobre 2026 : l'interface `http://pi-hole.chantevigne.com/`
affichait « site inaccessible » alors que Pi-hole fonctionnait (conteneur
`healthy` depuis 30 heures, aucun redémarrage, journal normal). Ces requêtes
échappaient aussi au blocage de Pi-hole.

**Correction.** Le 1er novembre 2026, le propriétaire a configuré le DHCP
DSM avec DNS1 `192.168.1.56` et DNS2 `192.168.1.57`, le Pi-hole secondaire.
Les deux serveurs distribués connaissent les mêmes noms locaux et filtrent
de la même façon ; le repli en cas d'arrêt d'une instance est conservé.

## Pi-hole secondaire

Un second Pi-hole, `192.168.1.57`, est déployé depuis `compose/pihole2/`
([ADR-0012](adr/0012-pihole-secondaire.md)). Déployé et validé le
1er novembre 2026 : listes et enregistrements locaux identiques sur les
deux instances. Déploiement, reconstruction et contrôles détaillés :
`compose/pihole2/README.md`.

### Architecture à deux instances

| | Principal | Secondaire |
|---|---|---|
| Conteneur, stack | `pihole`, `compose/pihole/` | `pihole2`, `compose/pihole2/` |
| LAN (macvlan `pihole_pihole_lan`) | `192.168.1.56` | `192.168.1.57` |
| Bridge `pihole_pihole_vpn` | `172.23.0.2` | `172.23.0.3` |
| Données `/etc/pihole` | `/volume1/docker/einstein/data/pihole` | `/volume1/docker/einstein/data/pihole2` |
| Distribution DHCP | DNS1 | DNS2 |

Le secondaire étend la définition Compose du principal (même image, mêmes
`dns.hosts`, amonts et options dnsmasq) et rejoint ses réseaux.
`nebula-sync` (`172.23.0.4`) copie le principal vers le secondaire toutes
les heures, par le bridge.

### Qui fait autorité

Chaque donnée a une seule source et un seul mécanisme de copie ; aucun ne
touche à ce que gère l'autre.

| Donnée | Source d'autorité | Copie vers les deux instances |
|---|---|---|
| Listes, domaines, groupes, clients (`gravity.db`) | interface du principal | nebula-sync (Teleporter), toutes les heures |
| Réglages modifiés dans l'interface | interface du principal | nebula-sync (API), toutes les heures |
| `dns.hosts`, amonts, options dnsmasq | `compose/pihole/compose.yaml` (`FTLCONF_`) | définition Compose partagée, au déploiement |
| Noms DHCP (`synology-hosts.list`) | baux du DHCP Synology | `sync-synology-dhcp-to-pihole.sh`, toutes les cinq minutes |

nebula-sync ne peut pas écraser les noms DHCP : `synology-hosts.list` n'est
pas un fichier de la sauvegarde Teleporter, et la directive `addn-hosts` qui
le charge est fixée par variable d'environnement sur les deux instances
(les réglages `FTLCONF_` ne sont pas modifiables par l'API). Inversement, le
script n'écrit que ce fichier. Une modification faite dans l'interface du
secondaire est écrasée à la synchronisation suivante.

Contrôle sur le NAS, avant puis après une synchronisation nebula-sync
(heure pleine) : empreintes et dates inchangées.

Vérifié le 1er novembre 2026 : nebula-sync a réécrit `gravity.db` du
secondaire à 20:00:06, tandis que les deux `synology-hosts.list` sont
restés à leur version de 19:23 (même empreinte SHA-256, 44 hôtes).

```bash
for c in pihole pihole2; do
  sudo docker exec "$c" sh -c \
    'sha256sum /etc/pihole/synology-hosts.list; stat -c %y /etc/pihole/synology-hosts.list'
done
```

### Ordre d'arrêt et de démarrage

- Démarrer `pihole` avant `pihole2` : la stack secondaire utilise les
  réseaux créés par la stack principale.
- Arrêter `pihole2` **avant** `stack-down.sh pihole` : Compose ne peut pas
  supprimer des réseaux encore utilisés par le secondaire.
- Pour une mise à jour, redéployer une instance à la fois et contrôler entre
  les deux : sans repli FRITZ!Box, arrêter les deux instances ensemble coupe
  la résolution DNS du LAN.

### Origine des requêtes acceptées

`FTLCONF_dns_listeningMode: "ALL"` est conservé pour les deux instances.
Le mode `LOCAL` (« Allow only local requests ») n'accepte que les réseaux
directement reliés au conteneur (`192.168.1.0/24`, `172.23.0.0/24`) et
risquerait de refuser les clients OpenVPN `10.8.0.0/24`, routés par le NAS.
`ALL` reste sûr tant qu'aucun port 53 n'est exposé à Internet : aucune
redirection vers `.56` ou `.57` n'est configurée sur la FRITZ!Box
(confirmé par le propriétaire le 1er novembre 2026), et Docker ne publie
aucun port. Le réglage étant fixé par variable d'environnement, il est
grisé dans l'interface et nebula-sync ne le modifie pas.

### Limite connue

Les deux instances tournent sur le même DS918+ et le même moteur Docker.
L'arrêt, la mise à jour ou la corruption d'un conteneur sont couverts ; un
arrêt ou une panne du NAS, de Docker ou du réseau macvlan coupe les deux
résolveurs. Pour l'administration, utiliser de préférence
`http://192.168.1.56/admin/`, et l'adresse IP du NAS en cas de panne DNS.

## Mises à jour

La version de l'image est fixée dans `compose/pihole/compose.yaml`. Avant une
mise à jour : lire les notes de version, sauvegarder avec `backup-stack.sh`
(interruption DNS brève), puis `git pull --ff-only` et `stack-up.sh pihole`.
Vérifier ensuite `pihole version`, `dns.upstreams`, `strict-order` et la
résolution depuis un client du LAN.

Le 25 octobre 2026 : passage de 2026.09.0 à 2026.10.0 (FTL v6.8, Web v6.6.1,
Core v6.5 ; 17 avis de sécurité corrigés, aucun changement incompatible
annoncé), après sauvegarde. `DATA_DIR` a été ajouté au `.env` NAS, après
contrôle du montage réel de `/etc/pihole`, pour permettre la sauvegarde.
Le propriétaire confirme les contrôles.

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
`synology-hosts.list` pour chaque conteneur de `PIHOLE_TARGETS`
(par défaut `pihole pihole2`), puis recharge FTL dans ce conteneur. Son
exécution nécessite root.

Le fichier est écrit dans le volume monté sur `/etc/pihole` de chaque
conteneur, lu par `docker inspect`, et le rechargement passe par
`docker exec` : le script n'utilise pas le réseau, donc la limite
hôte↔macvlan ne s'applique pas. Une cible inchangée n'est pas rechargée.

Une cible en échec (conteneur absent, volume introuvable, écriture ou
rechargement impossible) n'empêche pas de traiter les autres. Le script
termine alors avec le code 1 et un message
`ERREUR: synchronisation DHCP vers Pi-hole en échec pour : <conteneurs>`,
que reprend la notification DSM. Si le rechargement seul échoue, le fichier
est déjà écrit et FTL le lira au prochain démarrage. Arrêter un Pi-hole,
y compris pendant `backup-stack.sh`, provoque donc des notifications
d'échec jusqu'à son redémarrage. Pour une seule cible :

```bash
sudo PIHOLE_TARGETS=pihole2 scripts/sync-synology-dhcp-to-pihole.sh
```

Si aucun bail exploitable n'est trouvé, aucun fichier n'est modifié.

Chaque appel `docker` est limité à `DOCKER_TIMEOUT` secondes (30 par
défaut) ; un dépassement compte comme un échec de la cible. Le 3 novembre
2026, un `docker exec pihole` resté bloqué près de 17 heures a fait ignorer
toutes les exécutions suivantes (notification DSM « la tâche est déjà en
cours d'exécution »), sans effet sur le DNS. Le 4 novembre, même
`docker exec pihole true` et `docker exec pihole2 true` bloquaient : le démon
Docker ne lançait plus de commande dans les conteneurs, pendant une forte
charge disque (sauvegardes, charge ~11 dont ~10 d'attente disque, swap
2,9 Go). Rétabli en redémarrant Container Manager, avec une courte coupure DNS.
Test : `sudo timeout 10 docker exec pihole true; echo $?` (124 = bloqué).

La tâche planifiée DSM « Einstein - Sync DHCP vers Pi-hole » (root, toutes
les cinq minutes) exécute
`/bin/sh /var/services/homes/tonio/Development/Einstein/scripts/sync-synology-dhcp-to-pihole.sh`
sans variable : elle alimente les deux instances. Éviter une synchronisation
concurrente pendant une restauration.

Validé le 1er novembre 2026 après `git pull` du commit `1e7376f` : exécution
DSM de 19:40:02 en code 0, puis journaux de 19:55 et 20:00 indiquant
« aucun changement (44 hôtes) » pour `pihole` et `pihole2`. Test d'échec
avec `PIHOLE_TARGETS="pihole absent"` : `pihole` traité, message
`absent : conteneur introuvable` puis `en échec pour : absent`, code 1.
Depuis le Mac, `dig` renvoie la même adresse sur `.56` et `.57` pour les
hôtes DHCP contrôlés (`mac-mimi`, `ps5`, `iphone-tonio`, etc.).

La sortie des tâches DSM est conservée dans le dossier d'enregistrement du
Planificateur de tâches (`/volume1/Rapports Synology/Planificateur de tâches`).
Ces journaux recopient la commande de chaque tâche : réserver ce dossier aux
administrateurs et ne jamais placer de secret dans la commande d'une tâche.
