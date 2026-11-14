# Exploitation Docker

## Principes

Sur le Synology, les commandes Docker nécessitent `sudo`.

Les permissions du socket `/var/run/docker.sock` ne sont pas modifiées et
aucun groupe `docker` supplémentaire n'est créé.

## Mise à jour du dépôt sur le NAS

```bash
cd ~/Development/Einstein
git pull --ff-only
```

L'option `--ff-only` évite la création accidentelle d'un commit de fusion sur
le NAS.

## Préparer un nouveau service

Utiliser un vrai nom de service dans la variable `SERVICE` :

```bash
cd ~/Development/Einstein

SERVICE=smoke-test

cp -R compose/_template "compose/$SERVICE"
cd "compose/$SERVICE"

cp .env.example .env
chmod 600 .env
```

Les fichiers `.env` réels restent uniquement sur le NAS et ne sont jamais
versionnés.

## Créer les dossiers persistants

```bash
SERVICE=smoke-test

sudo install -d \
  -o tonio \
  -g users \
  -m 0750 \
  "/volume1/docker/einstein/data/$SERVICE" \
  "/volume1/docker/einstein/logs/$SERVICE"

sudo install -d \
  -o tonio \
  -g users \
  -m 0700 \
  "/volume1/docker/einstein/secrets/$SERVICE"
```

## Valider la configuration

Depuis le dossier du service :

```bash
sudo docker compose --env-file .env config
```

Cette commande doit réussir avant tout démarrage.

## Télécharger et démarrer

```bash
sudo docker compose --env-file .env pull
sudo docker compose --env-file .env up -d
```

## Contrôler le service

```bash
sudo docker compose --env-file .env ps
sudo docker compose --env-file .env logs --tail 200
```

Pour suivre les journaux :

```bash
sudo docker compose --env-file .env logs --tail 200 --follow
```

`Ctrl+C` quitte l'affichage sans arrêter les conteneurs.

## Arrêter le service

Arrêt simple :

```bash
sudo docker compose --env-file .env stop
```

Arrêt et suppression des conteneurs de la stack :

```bash
sudo docker compose --env-file .env down
```

L'option `--volumes` ne doit pas être utilisée sans analyse préalable.

## Commandes potentiellement destructrices

Les commandes suivantes sont interdites dans les opérations courantes :

```bash
sudo docker system prune
sudo docker volume prune
sudo docker network prune
```

Elles pourraient supprimer des ressources appartenant à des paquets DSM ou à
d'autres applications du NAS. Un nettoyage se fait par inventaire, puis
suppression de noms fixes écrits en toutes lettres (voir
[l'incident du 1er novembre 2026](incidents/2026-11-01-suppression-volume1.md)).

### Nettoyage du 11 novembre 2026

Inventaire (`docker system df -v`, contenu de chaque volume), puis
suppression par `docker rm`, `docker rmi` et `docker volume rm` nommés :

- conteneurs `Homebridge` (oznu, remplacé par la stack `homebridge`,
  [ADR-0015](adr/0015-homebridge-compose.md)) et `ldap-agent` (resté
  orphelin après la désinstallation de C2 Identity LDAP Agent le
  1er novembre : `project_id` illisible), avec réseau et images ;
- images inutilisées : `homebridge/homebridge:synology-2026-11-02`,
  `pihole/pihole` 2026.10.0 et 2026.09.0, `speedtest-ookla`, 14 anciennes
  constructions `einstein-core` sans nom ;
- 28 volumes sans conteneur, d'anciennes applications : openHAB, Plex,
  xTeVe, knxd (2020–2022), OwnTone (2024–2025), un MySQL 8 d'essai
  (28 avril 2026) et des volumes vides.

Les volumes sont archivés avant suppression dans
`/volume1/docker/einstein/backups/docker-volumes-orphelins-20261111.tar.gz`
(194 Mo, 2 764 entrées, archive vérifiée). Restent les images et conteneurs
des stacks du dépôt, `busybox:1.37.0` pour `smoke-test`, et aucun volume.

## Surveillance de la saturation

Prévention de l'[incident du 4 novembre 2026](incidents/2026-11-04-saturation-perte-ecritures.md) :
`scripts/nas-health-check.sh` affiche une ligne d'état et termine en erreur
(code 1, alertes sur la sortie d'erreur) si l'un de ces seuils est atteint :

| Contrôle | Seuil par défaut | Variable |
|---|---|---|
| `docker exec pihole true` | pas de réponse en 10 s | `DOCKER_PROBE`, `DOCKER_TIMEOUT` |
| attente disque (échantillon de 10 s) | ≥ 40 %, deux exécutions de suite | `IOWAIT_MAX`, `IOWAIT_RUNS`, `SAMPLE_SECONDS` |
| swap occupé | ≥ 2 048 Mo | `SWAP_USED_MAX_MB` |
| mémoire disponible | < 500 Mo | `MEM_AVAILABLE_MIN_MB` |
| RAID (`/proc/mdstat`) | grappe dégradée (`_` dans `[UU…]`) | — |

Un conteneur sonde arrêté (sauvegarde, maintenance) n'est pas une alerte ;
un démon Docker qui ne répond plus en est une. Le compteur d'attente disque
est conservé dans `/volume1/docker/einstein/tmp/nas-health-check.state`.
Valeurs de référence le 14 novembre 2026 : attente disque 0 %, swap 618 Mo,
mémoire disponible 5,3 Go ; pendant l'incident : charge ~11 dont ~10
d'attente disque, swap 2,9 Go, `docker exec` bloqué.

Tâche DSM (Planificateur de tâches, script défini par l'utilisateur) :

- nom « Einstein - Surveillance saturation », utilisateur root ;
- toutes les 15 minutes, toute la journée ;
- script :
  `/bin/sh /var/services/homes/tonio/Development/Einstein/scripts/nas-health-check.sh`
- paramètres : envoyer les détails par courriel **uniquement si le script
  se termine anormalement**.

### En cas d'alerte

1. Lire le courriel : la ligne d'état et les alertes indiquent la cause.
2. Ne **jamais** couper le NAS par l'interrupteur : des écritures non
   enregistrées seraient perdues, comme le 4 novembre.
3. Suspendre les tâches lourdes en cours : Hyper Backup (Swiss Backup,
   DS212j, locales), Glacier, nettoyage des données.
4. Attendre la baisse de l'attente disque et du swap (relancer la tâche
   depuis le Planificateur pour suivre l'état).
5. Si Docker reste bloqué : redémarrer Container Manager (courte coupure DNS),
   puis, en dernier recours, redémarrer le NAS **depuis DSM**.
6. Après tout arrêt non propre : chercher les fichiers vides écrits dans les
   heures précédentes, par exemple
   `sudo find /volume1/<dossier> -xdev -type f -size 0 -newermt "AAAA-MM-JJ HH:MM"`,
   et comparer avec les instantanés avant toute restauration.
7. Consigner l'événement dans `docs/incidents/`.

## Diagnostic

```bash
cd ~/Development/Einstein
./scripts/docker-doctor.sh
```

## Scripts standardisés

`stack-up.sh` distingue les images externes des images construites localement. Il télécharge les images non constructibles avec `pull --ignore-buildable`, puis exécute `up --build` afin de reconstruire les services possédant un `Dockerfile`.

Les stacks Einstein sont administrées depuis la racine du dépôt :

```bash
./scripts/stack-up.sh <service>
./scripts/stack-down.sh <service>
./scripts/stack-status.sh <service>
./scripts/stack-logs.sh <service>
# Pour une stack persistante avec DATA_DIR configuré :
./scripts/backup-stack.sh <service>
```

Exemple :

```bash
./scripts/stack-status.sh smoke-test
./scripts/stack-logs.sh smoke-test --tail 50
```

Sans option supplémentaire, `stack-logs.sh` affiche les 200 dernières lignes
puis suit les nouveaux journaux.

Le script de sauvegarde :

1. vérifie le service et son fichier `.env` ;
2. arrête temporairement les conteneurs actifs ;
3. archive le répertoire défini par `DATA_DIR` ;
4. calcule une empreinte SHA-256 ;
5. crée un manifeste avec le commit Git ;
6. redémarre la stack si elle fonctionnait avant la sauvegarde.

Les archives sont placées dans :

```text
/volume1/docker/einstein/backups/<service>/
```

La variable `DATA_DIR` couvre le stockage principal du service. Tout service
possédant plusieurs emplacements persistants doit documenter et étendre sa
procédure de sauvegarde.

## Périmètre de sauvegarde

`backup-stack.sh` archive uniquement le répertoire `DATA_DIR`. Il n'inclut ni
le `.env`, ni les secrets externes, ni la configuration DSM, ni les autres
volumes éventuels. `DATA_DIR` doit être un chemin absolu existant, écrit
explicitement dans le `.env` (sans interpolation de variable).

| Stack | Utilisation du script |
|---|---|
| `smoke-test` | `DATA_DIR` est défini dans l'exemple et monté sur `/data` |
| `pihole` | `DATA_DIR` est défini dans l'exemple et monté sur `/etc/pihole` ; voir la procédure dédiée |
| `einstein-core` | Depuis le Sprint 4, catalogue JSON sous `DATA_DIR`, monté en lecture seule ; procédure dans le guide Core |

Sur le NAS, le script ne relance pas automatiquement ses commandes de fichiers
avec `sudo` : l'exécuter avec `sudo` si les données appartiennent au conteneur
ou sont inaccessibles à l'utilisateur. Restreindre les permissions de la
destination avant la sauvegarde si elle contient des données sensibles.

La sauvegarde arrête temporairement la stack : pour Pi-hole, prévoir une
interruption DNS. Un piège de sortie tente le redémarrage si la stack était
active ; vérifier son état après l'opération, y compris après un échec.
Une stack partiellement active peut être entièrement redémarrée par le script.

Voir [la procédure Pi-hole](pihole-operations.md) pour les éléments à conserver
séparément et les contrôles de restauration. La présence d'une archive et
d'une empreinte ne remplace pas un test de restauration.
