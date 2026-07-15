# Sprint 2 — Socle Docker reproductible

- **Statut :** terminé et validé
- **Date de clôture :** 15 juillet 2026
- **Hôte de référence :** Synology DS918+ — DSM 7.2.2 Update 9

## Objectif

Construire un socle Docker propre, reproductible, sécurisé et documenté avant
l’installation des services applicatifs et des composants d’intelligence
artificielle d’Einstein.

Le principe retenu est :

```text
définir → configurer → déployer → vérifier → documenter → sauvegarder
```

## État initial observé

| Élément | Valeur validée |
|---|---|
| Processeur | 4 cœurs x86-64 |
| Mémoire détectée par Docker | 8,18 Go |
| Docker Engine | 24.0.2 |
| Docker Compose | 2.20.1 |
| Stockage Docker | `/volume1/@docker` |
| Système de fichiers | Btrfs |
| Pilote de logs DSM par défaut | `db` |
| Accès au moteur Docker | `sudo`, socket `root:root` |
| Conteneurs préexistants | Homebridge et `ldap-agent` |

Les conteneurs et volumes préexistants n’ont pas été modifiés.

## Architecture retenue

### Développement et déploiement

```text
VS Code sur le Mac
        │
        ▼
Dépôt Git local
        │
        ▼
GitHub privé
        │
        ▼
Deploy key NAS en lecture seule
        │
        ▼
Clone de déploiement sur le NAS
        │
        ▼
Docker Compose
```

Le Mac est l’environnement de développement. GitHub est la référence centrale.
Le NAS récupère les changements avec `git pull --ff-only` et ne pousse pas de
modification vers le dépôt.

### Séparation du code et des données

Le dépôt de déploiement est situé dans :

```text
/var/services/homes/tonio/Development/Einstein
```

Les données d’exécution sont conservées hors de Git :

```text
/volume1/docker/einstein/
├── data/
├── logs/
├── secrets/
├── backups/
└── tmp/
```

Le dossier `secrets` utilise des permissions plus restrictives.

## Livrables

### Conventions Docker Compose

Le modèle `compose/_template/` définit notamment :

- une image à version explicite ;
- `restart: unless-stopped` ;
- une limite mémoire ;
- une pondération CPU compatible DSM ;
- `no-new-privileges` ;
- la suppression des capacités Linux inutiles ;
- un système de fichiers en lecture seule lorsque possible ;
- un répertoire temporaire en mémoire ;
- la publication locale des ports d’administration ;
- des volumes persistants externes au dépôt.

### Service de validation

Le service `compose/smoke-test/` valide le socle avec un serveur HTTP BusyBox
minimal.

Il teste :

- le téléchargement d’une image versionnée ;
- la création d’un réseau Compose ;
- l’exécution avec l’UID `1026` et le GID `100` ;
- le système de fichiers racine en lecture seule ;
- l’écriture dans un volume persistant ;
- le healthcheck HTTP ;
- la limite mémoire de 64 Mio ;
- la pondération CPU `cpu_shares: 256` ;
- le pilote de logs rotatif `local` ;
- le bind du port sur `127.0.0.1:18080` ;
- la politique `restart: unless-stopped` ;
- le redémarrage et la persistance des données.

### Scripts d’exploitation

Les scripts suivants ont été ajoutés :

```text
scripts/
├── docker-doctor.sh
├── stack-up.sh
├── stack-down.sh
├── stack-status.sh
├── stack-logs.sh
├── backup-stack.sh
└── lib/
    └── stack-common.sh
```

Ils fournissent une interface uniforme :

```bash
./scripts/stack-up.sh smoke-test
./scripts/stack-down.sh smoke-test
./scripts/stack-status.sh smoke-test
./scripts/stack-logs.sh smoke-test
./scripts/backup-stack.sh smoke-test
```

### Sauvegarde

Le test de sauvegarde a validé :

- l’arrêt temporaire du service ;
- l’archivage du répertoire défini par `DATA_DIR` ;
- la création d’une archive horodatée ;
- le calcul d’une empreinte SHA-256 ;
- la création d’un manifeste ;
- l’enregistrement du commit Git ;
- le redémarrage du service lorsqu’il était actif.

Les sauvegardes sont stockées dans :

```text
/volume1/docker/einstein/backups/<service>/
```

## Limitation DSM découverte

Le noyau DSM du DS918+ ne prend pas en charge les quotas CPU CFS utilisés par
la propriété Compose `cpus`.

L’erreur observée était :

```text
NanoCPUs can not be set, as your kernel does not support CPU CFS scheduler
or the cgroup is not mounted
```

La décision retenue est donc :

```yaml
mem_limit: 64m
cpu_shares: 256
```

`mem_limit` impose une limite stricte de mémoire. `cpu_shares` fournit une
pondération relative lorsque plusieurs conteneurs sollicitent simultanément le
processeur ; il ne constitue pas une limite CPU maximale.

Cette décision est formalisée dans l’ADR-0004.

## Matrice de validation

| Critère | Résultat |
|---|---|
| Dépôt GitHub privé opérationnel | Validé |
| Deploy key NAS en lecture seule | Validé |
| `git pull --ff-only` depuis le NAS | Validé |
| Séparation code / données | Validé |
| Permissions des dossiers | Validé |
| Validation `docker compose config` | Validé |
| Déploiement Compose | Validé |
| Healthcheck | Validé |
| Port lié à `127.0.0.1` | Validé |
| Exécution non-root | Validé |
| Racine du conteneur en lecture seule | Validé |
| Volume persistant | Validé |
| Limite mémoire | Validé |
| Pondération CPU | Validé |
| Rotation des logs | Validé |
| Redémarrage | Validé |
| Scripts d’exploitation | Validé |
| Sauvegarde et manifeste SHA-256 | Validé |
| Cycle `down → up → contrôle HTTP` | Validé |
| Build MkDocs strict | Validé |

## Décisions associées

- ADR-0002 — Séparation du code et des données persistantes ;
- ADR-0003 — Gestion des services avec Docker Compose ;
- ADR-0004 — Gestion des ressources CPU sous DSM.

## Commandes de référence

Diagnostic :

```bash
cd ~/Development/Einstein
./scripts/docker-doctor.sh
```

État d’un service :

```bash
./scripts/stack-status.sh smoke-test
```

Déploiement :

```bash
./scripts/stack-up.sh smoke-test
```

Sauvegarde :

```bash
./scripts/backup-stack.sh smoke-test
```

## Clôture

Le Sprint 2 est terminé. Einstein dispose désormais d’un socle Docker
reproductible et exploitable.

Le Sprint 3 pourra se concentrer sur le socle applicatif : API Einstein,
configuration, secrets, persistance légère, endpoints de santé et préparation
des futurs agents et fournisseurs de modèles.
