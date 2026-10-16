# Einstein

> Plateforme personnelle d'intelligence artificielle auto-hébergée.

## Vision

Einstein est un assistant IA personnel conçu pour fonctionner 24h/24 sur une infrastructure privée.

Le projet a pour objectif de centraliser :

- la gestion de la maison ;
- les projets personnels ;
- l'enseignement ;
- l'automatisation ;
- la mémoire documentaire.

Les données restent sous le contrôle du propriétaire.

---

## Projet pilote

**Einstein Maison**

Premier domaine fonctionnel du projet.

---

## Infrastructure actuelle

- Synology DS918+
- DSM 7.2.2 Update 9
- 8 Go RAM
- Docker
- Homebridge
- Synology Mail Server
- Synology Drive
- VPN OpenVPN
- Développement sous VS Code

---

## Statut

🚧 Sprint 3 — socle applicatif en cours de finalisation.

Einstein Core expose les endpoints de santé et de version. La clôture du
sprint reste conditionnée à la documentation opérationnelle et à la
consolidation des validations NAS.

Voir la [roadmap](docs/roadmap.md) et le
[suivi du Sprint 3](docs/sprints/sprint-3-socle-applicatif.md).

## Développement local

Le développement se fait sur le Mac ; le NAS est la cible de déploiement.
Python 3.14 est requis.

Depuis la racine du dépôt :

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest
```

Démarrer l'API localement :

```bash
python -m uvicorn einstein_core.main:app --reload --host 127.0.0.1 --port 8000
```

Les endpoints sont accessibles sur `http://127.0.0.1:8000` :

- `/health/live` ;
- `/health/ready` ;
- `/version` ;
- `/docs` pour la documentation OpenAPI.

## Documentation

Les outils documentaires sont installés séparément des dépendances du Core :

```bash
python -m pip install 'mkdocs==1.6.1' 'mkdocs-material==9.7.6'
python -m mkdocs serve
```

Avant de soumettre des modifications :

```bash
python -m pytest
python -m mkdocs build --strict
git diff --check
```

Le déploiement du service est décrit dans
[compose/einstein-core/README.md](compose/einstein-core/README.md).
