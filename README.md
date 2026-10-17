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

Sprint 4 — premier inventaire Maison terminé.

Einstein Core expose les endpoints de santé et de version. Le socle est
testé et déployé sur le NAS ; les validations et leurs limites sont
consignées dans le suivi du sprint. L’inventaire Maison est déployé,
accessible sur le LAN et via VPN.

Voir la [roadmap](docs/roadmap.md) et le
[bilan du Sprint 4](docs/sprints/sprint-4-inventaire-maison.md).

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

Le catalogue d'exemple `config/equipements.example.json` est utilisé par défaut
lorsque la commande est lancée depuis la racine. Pour utiliser un autre fichier,
exporter `EINSTEIN_MAISON_INVENTORY_PATH` avec son chemin. Aucun fichier `.env`
n'est chargé automatiquement par Python.

Valider un catalogue avant utilisation (code de sortie 0 si valide, 1 sinon) :

```bash
python -m einstein_core.maison config/equipements.example.json
```

Démarrer l'API localement :

```bash
python -m uvicorn einstein_core.main:app --reload --host 127.0.0.1 --port 8000
```

Les endpoints sont accessibles sur `http://127.0.0.1:8000` :

- `/health/live` ;
- `/health/ready` ;
- `/version` ;
- `/docs` pour la documentation OpenAPI ;
- `/api/v1/maison/equipements` et `/api/v1/maison/equipements/{id}` pour l’inventaire.

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
