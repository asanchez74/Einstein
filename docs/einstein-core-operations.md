# Exploitation d'Einstein Core

## Périmètre

Einstein Core est une API FastAPI sans base de données ni secret applicatif.
Depuis le Sprint 4, elle dépend d'un catalogue JSON externe monté en lecture
seule. La procédure ci-dessous doit être appliquée avant son premier déploiement. Le développement local et les tests sont
décrits dans le README à la racine du dépôt.

## Configuration

| Variable | Valeur par défaut en Python | Valeur dans la stack | Usage |
|---|---|---|---|
| `EINSTEIN_APP_NAME` | `Einstein Core` | Non transmise par Compose | Nom exposé par l'API |
| `EINSTEIN_ENVIRONMENT` | `development` | `production` | `development`, `test` ou `production` |
| `EINSTEIN_LOG_LEVEL` | `INFO` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL` |
| `EINSTEIN_VERSION` | `0.1.0` | Non transmise par Compose | Version exposée ; conserver celle du paquet |
| `EINSTEIN_MAISON_INVENTORY_PATH` | `config/equipements.example.json` | `/inventory/equipements.json` | Catalogue chargé au démarrage |
| `DATA_DIR` | Sans objet | `/volume1/docker/einstein/data/einstein-core` | Répertoire source du montage Compose |
| `HOST_PORT` | Sans objet | `18081` | Port local du NAS, variable Compose |

Le fichier `compose/einstein-core/.env` sert à l'interpolation Compose.
Seules les variables déclarées dans `environment` sont transmises au conteneur.
En développement local, exporter les variables `EINSTEIN_` dans le shell :
l'application ne charge pas automatiquement un fichier `.env`.

La configuration est chargée au démarrage et mise en cache. Après modification
du `.env` NAS, relancer `stack-up.sh` pour appliquer la configuration et recréer
le conteneur si nécessaire ; un simple redémarrage ne recharge pas son environnement.

## Déployer sur le NAS

Les changements sont préparés, testés, committés et poussés depuis le Mac.
Sur le NAS :

```bash
cd ~/Development/Einstein
git pull --ff-only
git rev-parse HEAD
```

Lors du premier déploiement uniquement, créer le fichier local sans écraser
une configuration existante :

```bash
cd ~/Development/Einstein/compose/einstein-core
cp -n .env.example .env
chmod 600 .env
```

Préparer le catalogue avant déploiement (ne pas remplacer un fichier existant) :

```bash
sudo install -d -o 10001 -g 10001 -m 0750 /volume1/docker/einstein/data/einstein-core
sudo cp -n ~/Development/Einstein/config/equipements.example.json /volume1/docker/einstein/data/einstein-core/equipements.json
sudo chown 10001:10001 /volume1/docker/einstein/data/einstein-core/equipements.json
sudo chmod 0640 /volume1/docker/einstein/data/einstein-core/equipements.json
```

Adapter le catalogue aux équipements confirmés. Le RT2600ac est absent de
l'exemple tant que son rôle précis n'est pas confirmé. Renseigner `DATA_DIR`
dans le `.env` NAS pour permettre la sauvegarde. Le montage n'est pas créé
automatiquement si le répertoire manque ; le démarrage échoue si le fichier
est absent ou invalide.

Vérifier les valeurs du `.env`, puis valider et déployer :

```bash
cd ~/Development/Einstein/compose/einstein-core
sudo docker compose --env-file .env config --quiet
cd ~/Development/Einstein
./scripts/stack-up.sh einstein-core
```

Le script construit l'image locale et démarre la stack. Son succès ne signifie
pas que le healthcheck a déjà réussi : contrôler séparément l'état du service.

## Contrôles locaux au NAS

```bash
./scripts/stack-status.sh einstein-core
./scripts/stack-logs.sh einstein-core --tail 50
sudo docker inspect --format '{{.State.Health.Status}}' einstein-core
curl --fail --show-error http://127.0.0.1:18081/health/live
curl --fail --show-error http://127.0.0.1:18081/health/ready
curl --fail --show-error http://127.0.0.1:18081/version
```

Adapter le port si `HOST_PORT` a été modifié. Les réponses attendues sont
`{"status":"ok"}`, `{"status":"ready"}` et les métadonnées du service avec
l'environnement `production` pour la configuration NAS par défaut.

Le healthcheck interroge `/health/ready` toutes les 30 secondes. La readiness
est actuellement statique, puisque le service n'a aucune dépendance externe.
En cas d'état `unhealthy`, consulter les logs et le résultat du healthcheck :

```bash
sudo docker inspect --format '{{json .State.Health}}' einstein-core
sudo docker stats --no-stream einstein-core
```

La limite mémoire est de 256 Mio et la pondération CPU de 256. Les logs
applicatifs sont en JSON ; les logs Uvicorn ne sont pas explicitement
configurés avec ce formateur. Docker assure une rotation locale de 3 fichiers
de 10 Mo au maximum chacun.

## Reverse proxy et accès LAN/VPN

La politique retenue le 16 octobre 2026 autorise le LAN `192.168.1.0/24`
et OpenVPN `10.8.0.0/24`, sans accès depuis Internet. Les contrôles ont confirmé
la readiness HTTPS depuis le Mac sur le LAN sans VPN, puis via VPN.
Le contrôle externe de `/health/ready` a reçu HTTP 403. Voir le
[suivi du Sprint 3](sprints/sprint-3-socle-applicatif.md).

Configuration cible à vérifier dans DSM :

| Élément | Valeur |
|---|---|
| Source | HTTPS, `einstein.chantevigne.com`, port 443 |
| Destination | HTTP, `127.0.0.1`, port 18081 (ou `HOST_PORT`) |
| Certificat | Valide pour `einstein.chantevigne.com`, affecté à ce service |
| Contrôle d'accès | Autoriser `192.168.1.0/24` et `10.8.0.0/24`, refuser les autres sources |
| DNS | `einstein.chantevigne.com` vers `192.168.1.3`, fourni par Pi-hole |

Le contrôle d’accès LAN/VPN repose sur la configuration DSM et réseau. Le Core
ne possède actuellement aucune authentification ni restriction par adresse IP.
Le bind Docker sur `127.0.0.1` protège le port direct, mais ne définit pas la
politique d'accès au reverse proxy. Vérifier l'adresse source effectivement
vue par DSM et appliquer le contrôle au service Einstein.

Depuis le Mac sur le LAN sans VPN, puis connecté au VPN :

```bash
curl --fail --show-error --connect-timeout 5 --max-time 15 https://einstein.chantevigne.com/health/live
curl --fail --show-error --connect-timeout 5 --max-time 15 https://einstein.chantevigne.com/health/ready
curl --fail --show-error --connect-timeout 5 --max-time 15 https://einstein.chantevigne.com/version
```

Ouvrir également `https://einstein.chantevigne.com/docs`. Ne pas désactiver la
vérification TLS pour valider le certificat.

Depuis le LAN sans VPN, la readiness doit répondre `{"status":"ready"}`.
Si la résolution locale échoue, utiliser `curl --resolve
einstein.chantevigne.com:443:192.168.1.3` suivi de l'URL HTTPS.

Depuis une connexion Internet externe, par exemple un partage mobile avec
le Wi-Fi domestique et le VPN désactivés, aucun endpoint Einstein ne doit
être accessible. Noter le résultat exact (refus HTTP, refus de connexion ou
expiration). Un échec DNS seul ne démontre pas une restriction d'accès :
contrôler également les éventuelles redirections de ports et règles de proxy
existantes sur le chemin public. Ne pas utiliser l'adresse privée du NAS
pour démontrer un refus depuis Internet. Aucun port ne doit être ouvert
pour effectuer ce contrôle.

Le contrôle externe consigné dans le suivi du Sprint 3 confirme un refus
HTTP 403 pour `/health/ready` depuis la connexion testée. Rejouer ce contrôle
après toute modification des règles réseau ou du reverse proxy.

## Arrêt et redémarrage

Depuis la racine du dépôt NAS :

```bash
./scripts/stack-down.sh einstein-core
./scripts/stack-up.sh einstein-core
```

Rejouer les contrôles locaux et HTTPS après le redémarrage.

## Données et secrets

Le catalogue est monté en lecture seule sur `/inventory`. Le conteneur
ne modifie pas cette source. Pour changer le catalogue, préparer et valider
un nouveau fichier, conserver l'ancien, remplacer le fichier sur le NAS,
puis redémarrer le Core. Les changements de contenu ne sont pas rechargés
à chaud. Si le démarrage échoue, restaurer l'ancien fichier puis redémarrer.

Avec `DATA_DIR` explicite dans le `.env`, `sudo ./scripts/backup-stack.sh
einstein-core` archive le répertoire du catalogue en arrêtant brièvement le
service. Conserver aussi le `.env` séparément. Vérifier l'empreinte et le
contenu de l'archive. Pour restaurer, arrêter la stack, préserver le catalogue
actuel, extraire l'archive dans un répertoire de préparation, remettre le
catalogue sous `DATA_DIR` avec UID/GID `10001:10001` et les permissions de
lecture, puis démarrer et contrôler la santé et les routes Maison.
Cette restauration reste à valider sur le NAS.

Le Core ne lit actuellement aucun secret et ne prend en charge aucune variable
`*_FILE`. Lorsqu'une fonctionnalité nécessitera un secret, prévoir une lecture
explicite depuis un fichier monté en lecture seule, par exemple via Docker
Secrets, stocké hors Git sous `/volume1/docker/einstein/secrets/einstein-core/`.
Définir alors les permissions permettant la lecture par l'UID/GID `10001:10001`,
les tests, la rotation et la procédure de sauvegarde. Ce mécanisme reste à
implémenter avec le premier besoin applicatif ; ne pas ajouter une clé dans
l'image, les logs ou les exemples versionnés.

## Preuves à consigner pour la clôture

Conserver la date, le commit déployé, l'état healthy, les réponses HTTP locales
LAN et VPN, les résultats depuis Internet, le contrôle des ressources et le résultat du
redémarrage dans le suivi du Sprint 3. La validation du socle est consolidée
dans ce suivi, avec la chronologie et les limites des contrôles.
