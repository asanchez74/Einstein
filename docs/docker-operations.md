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

Elles pourraient supprimer des ressources appartenant à Homebridge, LDAP ou à
d'autres applications du NAS.

## Diagnostic

```bash
cd ~/Development/Einstein
./scripts/docker-doctor.sh
```
