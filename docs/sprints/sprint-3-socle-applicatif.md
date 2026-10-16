# Sprint 3 — Socle applicatif Einstein

## Statut

**En cours**

## Objectif

Construire le premier service applicatif de la plateforme Einstein sous la
forme d'une API légère, modulaire, testée et déployable sur le Synology.

## Socle technique

- Python 3.14 ;
- FastAPI ;
- Uvicorn ;
- Pydantic Settings ;
- pytest ;
- Docker Compose.

## Livrables

- [x] architecture applicative initiale ;
- [x] ADR sur le monolithe modulaire ;
- [x] structure Python sous `src/` ;
- [x] configuration par variables d'environnement ;
- [x] journalisation applicative structurée ;
- [x] endpoints `/health/live`, `/health/ready` et `/version` ;
- [x] premiers tests automatisés ;
- [x] Dockerfile et stack Compose ;
- [x] tests locaux validés ;
- [x] construction de l'image sur le NAS ;
- [x] healthcheck Docker validé ;
- [x] accès local sur `127.0.0.1` validé ;
- [x] intégration au reverse proxy Synology ;
- [ ] documentation opérationnelle finalisée ;
- [ ] gestion des secrets applicatifs documentée (aucun secret requis actuellement) ;
- [ ] preuves de validation NAS consolidées avec date et commit.

## Vérification locale du 16 octobre 2026

- Python 3.14.4 : 5 tests réussis ;
- build MkDocs strict réussi ;
- vérification de syntaxe Python et shell réussie ;
- `git diff --check` réussi.

Les tests couvrent les réponses nominales des trois endpoints et la
configuration par défaut ou par environnement. La readiness est statique :
le service ne dépend actuellement d'aucun service externe.

## Validations NAS et reste à clôturer

Les cases NAS cochées ci-dessus reprennent les validations déjà consignées
dans le projet. Elles n'ont pas été rejouées lors de la vérification locale.
La documentation initiale rapportait un accès HTTPS limité au VPN ; les
contrôles et la politique retenue le 16 octobre, consignés plus bas,
remplacent cette description.

Avant la clôture, compléter la procédure opérationnelle et consigner une
validation NAS datée, associée au commit déployé : construction de l'image,
healthcheck, endpoints locaux et via HTTPS/VPN, accès LAN et VPN, refus depuis Internet, redémarrage
et contrôle des ressources. Préciser également la gestion des futurs secrets.

Le Sprint 3 reste en cours. Aucune fonctionnalité métier ni intégration de
modèle IA n'est encore livrée.

## Contraintes

- aucun secret dans Git ;
- aucune exposition directe sur Internet ;
- conteneur non-root ;
- système de fichiers en lecture seule ;
- limite mémoire et pondération CPU compatibles DSM ;
- aucune base de données sans besoin démontré.

## Guide opérationnel du Core

Le [guide Einstein Core](../einstein-core-operations.md) décrit désormais la configuration, le déploiement,
les contrôles HTTP, le reverse proxy VPN et les futurs secrets. La clôture
documentaire reste ouverte jusqu'à la consolidation des validations NAS et
des autres points d'exploitation identifiés lors de l'audit.

## Clarifications d'exploitation

La [procédure Pi-hole](../pihole-operations.md) documente le périmètre des
sauvegardes, les éléments externes et les contrôles de restauration.
`DATA_DIR` est partagé entre le volume Compose et le script de sauvegarde ;
les `.env` NAS existants doivent être complétés avant utilisation du script.
La sauvegarde et la restauration Pi-hole restent à valider sur le NAS.

Les noms DNS `router` et `router.chantevigne.com` sont corrigés vers
`192.168.1.2` (Synology RT2600ac), après confirmation du propriétaire.
La résolution reste à vérifier après déploiement sur le NAS.

## Tests complémentaires du 16 octobre 2026

La suite comporte désormais 8 tests, tous réussis localement. Deux cas
vérifient le rejet d'un environnement et d'un niveau de logs invalides. Un
test contrôle les événements de démarrage et d'arrêt via le contexte
`TestClient`. Les tests HTTP existants exécutent également le lifespan.
Aucun changement du code applicatif n'a été nécessaire.

## Contrôle NAS du 16 octobre 2026 — clôture non validée

Contrôles effectués en lecture seule depuis le Mac par SSH via OpenVPN :

| Contrôle | Résultat |
|---|---|
| Hôte | `CHANTEVIGNE`, x86_64, DSM 7.2.2 Update 9 |
| Commit du clone NAS | `1d9827585793cbe5d3edb108c8c1451df2a9225d` |
| État Git NAS | `compose/pihole/compose.yaml` modifié ; fichier `compose.yaml.bak-20261014` non suivi dans la même stack |
| Port Core configuré | `HOST_PORT=18081` |
| HTTP local `/version` | Connexion refusée sur `127.0.0.1:18081` |
| HTTPS `/health/ready` depuis le Mac | HTTP 502 |
| Inspection Docker | Non effectuée : `sudo -n` exige un mot de passe |

La session SSH non interactive ne contient pas `/usr/local/bin` dans son
PATH ; Git a été interrogé via `/usr/local/bin/git`.

Le diff Pi-hole du NAS ajoute des noms DNS locaux et porte `cpu_shares` à
`2048` (contre `256` dans le dépôt Mac). Les noms locaux sont déjà représentés
dans le dépôt Mac ; la correction de `router` vers `192.168.1.2` est préparée
localement. La pondération CPU doit être réconciliée avant mise à jour du NAS.
Aucun fichier NAS n'a été modifié et aucun conteneur n'a été redémarré.

Ces résultats ne permettent pas de conclure que le conteneur est arrêté :
l'état Docker et les logs restent à examiner dans une session avec sudo.
Les validations historiques cochées plus haut ne constituent pas une
validation du déploiement actuel. Le Sprint 3 reste ouvert.

## Remise en service du Core le 16 octobre 2026

Les sorties terminal fournies par le propriétaire complètent le contrôle
initial : le conteneur `einstein-core:0.1.0` était arrêté (`Exited (143)`).
Ses logs montrent un arrêt propre le 14 octobre à 09:02:40 UTC ; ils ne
permettent pas d'en établir la cause.

Le propriétaire a relancé le conteneur existant avec
`docker compose --env-file .env start api`, sans reconstruire l'image.

| Contrôle après remise en service | Résultat transmis |
|---|---|
| HTTP local `/health/ready` depuis le NAS | `{"status":"ready"}` |
| Healthcheck Docker | `healthy` |
| Politique de redémarrage | `unless-stopped` |
| État OOMKilled inspecté | `false` |
| HTTPS `/health/ready` depuis le NAS | HTTP 403 |
| HTTPS `/health/ready` depuis le Mac connecté au VPN | `{"status":"ready"}` |

Le refus depuis le NAS est compatible avec une restriction aux clients VPN,
mais ne remplace pas un contrôle depuis un client hors VPN. L'image existante
n'a pas été reliée à un commit de construction ; le commit du clone NAS
consigné plus haut n'est pas une preuve de provenance de cette image.

Restent à consigner : refus depuis une connexion Internet externe, `/health/live` et
`/version` après redémarrage, ressources du conteneur, puis validation du
build et du déploiement final après réconciliation Git du NAS. La cause de
l'arrêt antérieur reste inconnue. Le Sprint 3 reste ouvert.

## Contrôle LAN hors VPN du 16 octobre 2026 — écart confirmé

Le propriétaire confirme que le Mac était connecté au LAN et que le VPN
était déconnecté lors du contrôle suivant :

```bash
curl --show-error --connect-timeout 5 --max-time 10 \
  --resolve einstein.chantevigne.com:443:192.168.1.3 \
  https://einstein.chantevigne.com/health/ready
```

Réponse obtenue : `{"status":"ready"}`. L'accès HTTPS depuis le LAN sans VPN
est donc autorisé dans la configuration actuelle. Cela contredit la politique
cible « VPN uniquement » décrite dans le guide opérationnel. Le refus HTTP
403 depuis le NAS ne suffit pas à démontrer cette restriction.

Avant clôture, confirmer la politique souhaitée (VPN uniquement ou LAN et
VPN), vérifier les règles d'accès réellement appliquées au reverse proxy DSM,
puis aligner configuration et documentation. L'accès depuis Internet reste
non vérifié ; le résultat LAN ne permet pas de conclure à une exposition
publique. Aucune règle DSM n'a été modifiée pendant ces contrôles.

## Politique d'accès retenue le 16 octobre 2026

Le propriétaire choisit d'autoriser le LAN `192.168.1.0/24` et le VPN
`10.8.0.0/24`, sans accès Internet. Cette décision remplace la cible initiale
« VPN uniquement » : le résultat LAN ci-dessus est conforme à la politique
retenue. Le guide opérationnel et le README du service sont alignés.

La readiness HTTPS est vérifiée sur le LAN et via VPN. Le refus depuis
Internet reste non vérifié, de même que les règles DSM effectives. Aucune
règle réseau n'a été modifiée. Le Sprint 3 reste ouvert.

## Contrôle Internet externe — refus HTTP confirmé

Depuis la connexion externe utilisée pour le contrôle, le propriétaire a
transmis les en-têtes de `https://einstein.chantevigne.com/health/ready` :

```text
HTTP/2 403
server: nginx
date: Fri, 16 Oct 2026 21:39:04 GMT
content-type: text/html
```

L'en-tête Date correspond au 16 octobre 2026 à 23:39:04 en Europe/Zurich.
Le corps HTML Synology « page introuvable » reçu précédemment accompagne
ce refus ; il ne s'agissait pas d'une réponse de readiness du Core.

La matrice observée pour `/health/ready` est désormais : LAN sans VPN autorisé,
VPN autorisé, connexion Internet externe testée refusée (403). Le point
d'entrée HTTPS public répond, mais refuse cette requête. Ce contrôle ciblé
ne constitue pas un audit de tous les ports, routes ou accès IPv6.

Restent avant clôture : contrôles `/health/live` et `/version`, ressources,
réconciliation des modifications Git du NAS, validation du build et du
déploiement final. Les changements locaux préparés restent non déployés.

## Endpoints et ressources après remise en service

Sorties fournies par le propriétaire lors de la même séquence de validation :

| Contrôle NAS | Résultat |
|---|---|
| HTTP local `/health/live` | `{"status":"ok"}` |
| HTTP local `/version` | `{"name":"Einstein Core","version":"0.1.0","environment":"production"}` |
| CPU instantané | 0,25 % |
| Mémoire utilisée / limite | 47,21 Mio / 256 Mio (18,44 %) |

Le relevé `docker stats --no-stream` décrit un instant après redémarrage,
sans test de charge ; il ne mesure pas les pics ni la stabilité prolongée.
La colonne PIDS indique 0 dans la sortie fournie et ne permet pas de
confirmer le nombre de processus du conteneur.

Les trois endpoints du Core existant sont désormais vérifiés. La clôture
reste conditionnée à la réconciliation Git NAS et à la validation du build
et du déploiement final. Aucune mise à jour du clone ni reconstruction de
l'image n'a été réalisée pendant ces contrôles.

## Réconciliation de la pondération CPU Pi-hole

Le propriétaire choisit de conserver `cpu_shares: 2048` pour Pi-hole.
Le fichier Compose du dépôt est aligné sur cette valeur ; Einstein Core
conserve 256. Cela résout le choix de pondération identifié dans le diff NAS,
sans modifier la limite mémoire Pi-hole de 512 Mio. La réconciliation Git
NAS et le déploiement des changements préparés restent à effectuer.
