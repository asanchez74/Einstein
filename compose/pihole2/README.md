# Pi-hole secondaire

Second résolveur DNS du LAN, à côté du Pi-hole principal `192.168.1.56`
(stack [`compose/pihole/`](../pihole/compose.yaml)). Décision et limites :
[ADR-0012](../../docs/adr/0012-pihole-secondaire.md).

## Architecture

```text
                       LAN 192.168.1.0/24 (macvlan pihole_pihole_lan, ovs_bond0)
   clients ──DNS──►  192.168.1.56 pihole        192.168.1.57 pihole2
                          │                          │
                   172.23.0.2 ──── bridge pihole_pihole_vpn ──── 172.23.0.3
                                         │
                                  172.23.0.4 nebula-sync
                                  toutes les heures : principal → secondaire
```

| Élément | Valeur |
|---|---|
| Conteneur | `pihole2`, sur le DS918+ |
| Adresse LAN (macvlan) | `192.168.1.57` |
| Adresse bridge | `172.23.0.3` |
| Données | `/volume1/docker/einstein/data/pihole2` |
| Image | celle du principal (`extends`), actuellement `pihole/pihole:2026.10.1` |
| Synchronisation | `nebula-sync` `v0.11.3`, `FULL_SYNC=true`, `RUN_GRAVITY=true`, `CRON=0 * * * *` |

Points de conception :

- **Une seule définition.** Le service `pihole` de cette stack étend celui de
  `compose/pihole/compose.yaml` : image, enregistrements `dns.hosts`, amonts,
  `strict-order`, `addn-hosts` et ressources sont identiques par construction.
  Une modification du principal se redéploie sur les deux stacks.
- **Réseaux partagés.** Docker refuse un second réseau macvlan sur
  `ovs_bond0` ; le secondaire rejoint donc les réseaux créés par la stack
  `pihole`, qui doit être démarrée en premier.
- **nebula-sync sur le NAS.** L'hôte ne joint pas ses conteneurs macvlan,
  mais deux conteneurs d'un même bridge se joignent : nebula-sync parle aux
  deux Pi-hole par `172.23.0.2` et `172.23.0.3`, sans port publié.
- **Ce que copie nebula-sync.** La sauvegarde Teleporter du principal
  (listes, domaines, groupes, clients) est importée dans le secondaire ;
  FTL ignore le `pihole.toml` de l'archive, et la configuration est copiée
  ensuite par l'API. Gravity est enfin reconstruit. Les réglages fixés par
  variables `FTLCONF_` restent ceux de la définition Compose.
- **Ce qu'il ne copie pas.** `synology-hosts.list` (noms DHCP) n'est pas
  dans la sauvegarde Teleporter : le script de synchronisation DHCP doit
  écrire aussi dans le volume du secondaire (voir plus bas).
- **Même mot de passe.** Les deux stacks utilisent le même secret
  `pihole_webpasswd.txt`, dont sont dérivés les secrets de nebula-sync.

## Prérequis

1. `192.168.1.57` est libre : hors plage dynamique du DHCP DSM, sans
   réservation, et sans réponse depuis le Mac. Un poste qui garde un ancien
   bail peut encore l'occuper ; attendre qu'il ait changé d'adresse.

   ```bash
   # Mac : aucune réponse et aucune entrée ARP attendues
   ping -c3 192.168.1.57; arp -n 192.168.1.57
   ```

2. La stack `pihole` fonctionne et ses réseaux existent :

   ```bash
   # NAS
   sudo docker network ls --filter name=pihole_
   ```

   Si les noms diffèrent de `pihole_pihole_lan` et `pihole_pihole_vpn`,
   les reporter dans le `.env`.

## Déploiement et reconstruction

La procédure est la même pour une première installation et pour une
reconstruction (perte ou corruption du volume) : tout l'état utile du
secondaire vient du principal. Sur le NAS, depuis le clone à jour
(`git pull --ff-only`) :

```bash
cd ~/Development/Einstein

# 1. Données (vide pour une reconstruction ; conserver l'ancien répertoire à part)
sudo install -d -m 0755 /volume1/docker/einstein/data/pihole2

# 2. Configuration locale
cp compose/pihole2/.env.example compose/pihole2/.env
chmod 600 compose/pihole2/.env
vi compose/pihole2/.env   # adresses, UPSTREAM_DNS identique au principal

# 3. Secrets nebula-sync, dérivés du mot de passe Web existant
#    (conteneur exécuté en UID 1001 ; le mot de passe ne doit contenir ni « | » ni « , »)
cd /volume1/docker/einstein/secrets
sudo sh -c 'umask 077
  P=$(cat pihole_webpasswd.txt)
  printf "http://172.23.0.2|%s" "$P" > nebula_sync_primary.txt
  printf "http://172.23.0.3|%s" "$P" > nebula_sync_replicas.txt'
sudo chown 1001 nebula_sync_primary.txt nebula_sync_replicas.txt
sudo chmod 400 nebula_sync_primary.txt nebula_sync_replicas.txt
cd ~/Development/Einstein

# 4. Démarrage (nebula-sync attend que pihole2 soit healthy)
sudo scripts/stack-up.sh pihole2
scripts/stack-status.sh pihole2
scripts/stack-logs.sh pihole2 --tail 50

# 5. Noms DHCP Synology dans le volume du secondaire
sudo PIHOLE_TARGETS=pihole2 scripts/sync-synology-dhcp-to-pihole.sh
```

La tâche planifiée DSM, toutes les cinq minutes, alimente ensuite les deux
instances (cibles par défaut `pihole pihole2`, voir
`docs/pihole-operations.md`).

Attendre une première synchronisation dans le journal de `nebula-sync`.
Si elle n'a pas lieu au démarrage, elle intervient à l'heure pleine suivante.

## Vérifications

Depuis le Mac sur le LAN (pas depuis le NAS) :

```bash
dig +short @192.168.1.57 nas.chantevigne.com      # attendu : 192.168.1.3
dig +short @192.168.1.57 example.org
dig +short @192.168.1.57 doubleclick.net          # attendu : 0.0.0.0 (bloqué)
```

Sur le NAS, les empreintes doivent être identiques pour les deux conteneurs :

```bash
# Listes, domaines, groupes et clients
for c in pihole pihole2; do
  printf '%s ' "$c"
  sudo docker exec "$c" pihole-FTL sqlite3 -readonly /etc/pihole/gravity.db \
    "SELECT address, enabled FROM adlist ORDER BY address;
     SELECT type, domain, enabled FROM domainlist ORDER BY type, domain;
     SELECT name, enabled FROM \"group\" ORDER BY name;
     SELECT ip FROM client ORDER BY ip;" | sha256sum
done

# Enregistrements locaux (dns.hosts et noms DHCP)
for c in pihole pihole2; do
  printf '%s ' "$c"
  sudo docker exec "$c" sh -c \
    'pihole-FTL --config dns.hosts; cat /etc/pihole/synology-hosts.list' | sha256sum
done

# Domaines dans gravity : proches, un écart est possible si une liste
# a changé entre deux exécutions de gravity
for c in pihole pihole2; do
  sudo docker exec "$c" pihole-FTL sqlite3 -readonly /etc/pihole/gravity.db \
    'SELECT COUNT(*) FROM gravity;'
done
```

### Déploiement du 1er novembre 2026

Commit `221f112`, Docker Compose v2.20.1 sur le NAS. `pihole2` et
`nebula-sync` sont `healthy` ; `nebula-sync` fonctionne en `read_only`.
La première synchronisation a lieu au démarrage (« Sync completed »).

- Mac : `.56` et `.57` donnent les mêmes réponses pour `nas`, `einstein`,
  `router`, `pi-hole`, deux noms DHCP et `example.org` ; `doubleclick.net`
  est bloqué (`0.0.0.0`) sur les deux. `nas.chantevigne.com` → `192.168.1.3`.
- MAC de `192.168.1.57` : `02:42:c0:a8:01:39`, dérivée de l'IP par Docker,
  réservée par le propriétaire dans le DHCP DSM. Elle pourrait changer avec
  une version de Docker qui ne dérive plus la MAC de l'IP.
- NAS : empreintes identiques pour les listes, domaines, groupes et clients,
  ainsi que pour `dns.hosts` et `synology-hosts.list` (44 hôtes) ; 2 listes
  et 155 301 domaines dans gravity sur les deux instances.

Le même jour, le propriétaire a configuré le DHCP DSM : DNS1
`192.168.1.56`, DNS2 `192.168.1.57`. La FRITZ!Box n'est plus distribuée.

## Exploitation

- **Ordre.** Démarrer `pihole` avant `pihole2`. Pour arrêter la stack
  principale avec `stack-down.sh`, arrêter d'abord `pihole2` : Compose ne
  peut pas supprimer des réseaux encore utilisés.
- **Mise à jour d'image.** Une seule ligne dans `compose/pihole/compose.yaml`.
  Redéployer `pihole`, contrôler, puis `pihole2` : un résolveur reste
  disponible pendant chaque redémarrage.
- **Modifications.** Les faire uniquement sur le principal (interface
  `http://192.168.1.56/admin/`). Une modification sur le secondaire est
  écrasée à la synchronisation suivante.
- **Effet horaire.** L'import et gravity redémarrent la résolution du
  secondaire quelques secondes chaque heure ; le principal n'est pas touché.
- **Sauvegarde.** `sudo scripts/backup-stack.sh pihole2` fonctionne
  (`DATA_DIR` du `.env`) mais n'est pas indispensable : la reconstruction
  ci-dessus repart du principal.
- **DHCP.** Les clients reçoivent les deux Pi-hole : arrêter les deux à la
  fois coupe la résolution sur le LAN, sans repli FRITZ!Box.
