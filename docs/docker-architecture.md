# Architecture Docker

## Objectif

Définir un socle Docker reproductible, sécurisé et adapté aux ressources du
Synology DS918+ hébergeant Einstein.

## Hôte de référence

| Élément | Valeur |
|---|---|
| NAS | Synology DS918+ |
| Système | DSM 7.2.2 Update 9 |
| Processeur | 4 cœurs x86-64 |
| Mémoire | 8 Go |
| Docker Engine | 24.0.2 |
| Docker Compose | 2.20.1 |
| Stockage Docker | `/volume1/@docker` |
| Système de fichiers | Btrfs |
| Pilote de logs DSM | `db` |

## Séparation entre code et données

Le dépôt Git contient uniquement les éléments reproductibles :

```text
/var/services/homes/tonio/Development/Einstein/
├── agents/
├── compose/
├── config/
├── docs/
├── scripts/
├── src/
├── tests/
└── workflows/

```

Le développement se fait sur le Mac. Le clone NAS sert au déploiement et est
mis à jour avec `git pull --ff-only`.

Les données d'exécution restent hors du dépôt :

```text
/volume1/docker/einstein/
├── data/
├── logs/
├── secrets/
├── backups/
└── tmp/
```

Voir l'[ADR-0002](adr/0002-separation-code-donnees.md).

## Modèle Compose

Le modèle `compose/_template/` définit les limites mémoire, la pondération CPU,
la publication locale des ports, la racine en lecture seule et la rotation des
logs avec le pilote `local`, validé au Sprint 2. Les quotas `cpus` sont exclus
sur cet hôte conformément à l'[ADR-0004](adr/0004-gestion-ressources-cpu-dsm.md).

Pour chaque service, adapter l'utilisateur, les volumes et le healthcheck aux
besoins et aux outils de l'image. Le healthcheck du modèle est un exemple
commenté à configurer avant le déploiement.

Exemple de configuration dans `.env`, à adapter depuis `.env.example` :

```dotenv

COMPOSE_PROJECT_NAME=einstein-service

IMAGE=registry.example.com/application:1.0.0

TZ=Europe/Zurich

HOST_PORT=18080
CONTAINER_PORT=8080

DATA_DIR=/volume1/docker/einstein/data/service
LOG_DIR=/volume1/docker/einstein/logs/service

MEM_LIMIT=512m
CPU_SHARES=256

```

<!-- BEGIN SPRINT_2_VALIDATION -->
## Validation du socle

Le service `compose/smoke-test/` a validé l’architecture Docker sur le DS918+ :

- image versionnée ;
- Docker Compose ;
- exécution non-root ;
- racine en lecture seule ;
- volume persistant ;
- healthcheck ;
- limite mémoire ;
- pondération CPU compatible DSM ;
- journalisation avec rotation ;
- port publié uniquement sur `127.0.0.1` ;
- redémarrage ;
- sauvegarde avec manifeste et SHA-256.

La clôture complète est documentée dans
[Sprint 2 — Socle Docker reproductible](sprints/sprint-2-socle-docker.md).
<!-- END SPRINT_2_VALIDATION -->
