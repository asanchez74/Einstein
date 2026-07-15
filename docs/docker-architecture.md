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
├── tests/
└── workflows/

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
├── tests/
└── workflows/


COMPOSE_PROJECT_NAME=einstein-service

IMAGE=registry.example.com/application:1.0.0

TZ=Europe/Zurich

HOST_PORT=18080
CONTAINER_PORT=8080

DATA_DIR=/volume1/docker/einstein/data/service
LOG_DIR=/volume1/docker/einstein/logs/service

MEM_LIMIT=512m
CPU_LIMIT=1.0
