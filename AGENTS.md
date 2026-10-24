# Einstein — Instructions de développement

## Projet

Einstein est une plateforme personnelle d'intelligence artificielle
auto-hébergée sur un Synology DS918+.

Le développement est effectué sur macOS avec VS Code.
Le Synology est une cible de déploiement, pas l'environnement principal
de développement.

## Git et déploiement

Dépôt GitHub privé : asanchez74/Einstein

Workspace de développement :
/Users/tonio/Development/Einstein

Clone de déploiement NAS :
/var/services/homes/tonio/Development/Einstein

Ne jamais modifier directement le code du dépôt sur le NAS.

Workflow normal :

1. modifier sur le Mac ;
2. exécuter les tests ;
3. vérifier les diffs ;
4. commit ;
5. push ;
6. sur le NAS : git pull --ff-only ;
7. déployer avec les scripts du dépôt.

Ne jamais committer de secrets ou de fichiers `.env`.

## Infrastructure

NAS : Synology DS918+
DSM : 7.2.2
Architecture : x86_64
RAM : environ 8 Go

Données runtime :
/volume1/docker/einstein/

Sous-répertoires :
- data
- logs
- secrets
- backups
- tmp

Les opérations Docker sur le NAS nécessitent sudo.

Le kernel DSM ne supporte pas correctement les quotas CPU CFS.
Ne pas utiliser `cpus:` dans Docker Compose.

Utiliser :
- `mem_limit`
- `cpu_shares`

Voir ADR-0004.

## Docker

Respecter les conventions existantes :

- utilisateurs non-root lorsque possible ;
- `read_only: true` lorsque possible ;
- `no-new-privileges` ;
- `cap_drop: ALL` lorsque possible ;
- healthcheck ;
- limites mémoire ;
- cpu_shares ;
- rotation des logs ;
- ports d'administration exposés uniquement localement si possible.

Réutiliser les scripts :
- scripts/stack-up.sh
- scripts/stack-down.sh
- scripts/stack-status.sh
- scripts/stack-logs.sh
- scripts/backup-stack.sh

Ne jamais lancer de `docker system prune --volumes`.

## Réseau

LAN : 192.168.1.0/24
FRITZ!Box : 192.168.1.1
NAS : 192.168.1.3
Pi-hole LAN : 192.168.1.56

OpenVPN : 10.8.0.0/24

Pi-hole VPN bridge :
172.23.0.0/24
Pi-hole : 172.23.0.2

DNS LAN et VPN : Pi-hole.

Pi-hole upstream :
FRITZ!Box 192.168.1.1, puis Quad9 9.9.9.9 en secours uniquement
(`strict-order`, bascule sur SERVFAIL/REFUSED ou absence de réponse).

FRITZ!Box utilise Quad9 via DNS-over-TLS, avec un second serveur DoT
de repli depuis l'incident du 24.10.2026.

Le Synology DHCP est la source de vérité pour les noms LAN
`*.chantevigne.com`.

Le script
`scripts/sync-synology-dhcp-to-pihole.sh`
synchronise les baux DHCP Synology vers Pi-hole.

## Einstein Core

Architecture : monolithe modulaire léger.

Langage : Python 3.14
Framework : FastAPI

Endpoints existants :
- /health/live
- /health/ready
- /version

Configuration via variables d'environnement préfixées `EINSTEIN_`.

Ne pas introduire PostgreSQL, Qdrant ou une autre infrastructure
sans besoin applicatif démontré.

## Tests

Avant de considérer une modification terminée :

- lancer les tests Python ;
- lancer compileall si pertinent ;
- lancer `git diff --check` ;
- vérifier le diff ;
- pour les modifications documentaires : `mkdocs build --strict`.

Ne pas masquer un test défaillant pour faire passer le build.

## Documentation

Les décisions d'architecture structurantes doivent être documentées
dans une ADR.

Mettre à jour la roadmap et les documents de sprint lorsque
l'état du projet change.

## Style de travail

Avant une modification importante :

1. inspecter le code existant ;
2. expliquer brièvement le plan ;
3. effectuer des changements petits et cohérents ;
4. tester ;
5. présenter le diff et les résultats.

Éviter les refactorings non demandés.

Ne pas introduire de dépendance inutile.

Préférer une architecture simple et évolutive à une architecture
complexe anticipant des besoins hypothétiques.