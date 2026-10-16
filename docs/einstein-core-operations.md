# Exploitation d'Einstein Core

## Périmètre

Einstein Core est une API FastAPI sans base de données, sans donnée persistante
et sans secret applicatif à ce stade. Le développement local et les tests sont
décrits dans le README à la racine du dépôt.

## Configuration

| Variable | Valeur par défaut en Python | Valeur dans la stack | Usage |
|---|---|---|---|
| `EINSTEIN_APP_NAME` | `Einstein Core` | Non transmise par Compose | Nom exposé par l'API |
| `EINSTEIN_ENVIRONMENT` | `development` | `production` | `development`, `test` ou `production` |
| `EINSTEIN_LOG_LEVEL` | `INFO` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL` |
| `EINSTEIN_VERSION` | `0.1.0` | Non transmise par Compose | Version exposée ; conserver celle du paquet |
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

## Reverse proxy et accès VPN

Configuration cible à vérifier dans DSM :

| Élément | Valeur |
|---|---|
| Source | HTTPS, `einstein.chantevigne.com`, port 443 |
| Destination | HTTP, `127.0.0.1`, port 18081 (ou `HOST_PORT`) |
| Certificat | Valide pour `einstein.chantevigne.com`, affecté à ce service |
| Contrôle d'accès | Autoriser `10.8.0.0/24`, refuser les autres sources |
| DNS | `einstein.chantevigne.com` vers `192.168.1.3`, fourni par Pi-hole |

La restriction VPN est assurée par la configuration DSM et réseau. Le Core
ne possède actuellement aucune authentification ni restriction par adresse IP.
Le bind Docker sur `127.0.0.1` protège le port direct, mais ne définit pas la
politique d'accès au reverse proxy. Vérifier l'adresse source effectivement
vue par DSM et appliquer le contrôle au service Einstein.

Depuis le Mac connecté au VPN :

```bash
curl --fail --show-error --connect-timeout 5 --max-time 15 https://einstein.chantevigne.com/health/live
curl --fail --show-error --connect-timeout 5 --max-time 15 https://einstein.chantevigne.com/health/ready
curl --fail --show-error --connect-timeout 5 --max-time 15 https://einstein.chantevigne.com/version
```

Ouvrir également `https://einstein.chantevigne.com/docs`. Ne pas désactiver la
vérification TLS pour valider le certificat.

Rejouer le contrôle hors VPN depuis le LAN, puis depuis une connexion externe :
aucun endpoint Einstein ne doit être accessible. Noter le résultat exact
(refus HTTP, refus de connexion ou expiration). Un échec DNS seul ne prouve
pas que le reverse proxy refuse l'accès ; si le NAS est joignable, vérifier
également avec `curl --resolve einstein.chantevigne.com:443:192.168.1.3` suivi
de l'URL HTTPS. Aucun port ne doit être ouvert sur le routeur pour ce test.

Le projet rapporte des validations VPN et hors VPN antérieures. Cette procédure
ne constitue pas une nouvelle preuve de validation du NAS.

## Arrêt et redémarrage

Depuis la racine du dépôt NAS :

```bash
./scripts/stack-down.sh einstein-core
./scripts/stack-up.sh einstein-core
```

Rejouer les contrôles locaux et HTTPS après le redémarrage.

## Données et secrets

Aucun volume persistant n'est monté pour le Core. Sa reconstruction repose sur
Git et sur le `.env` NAS. `backup-stack.sh` exige un `DATA_DIR` et ne s'applique
pas à cette stack sans état. Ne pas créer de répertoire de données artificiel.

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
et VPN, les résultats hors VPN, le contrôle des ressources et le résultat du
redémarrage dans le suivi du Sprint 3. La validation NAS reste à consolider.
