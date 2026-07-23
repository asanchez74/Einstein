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
- [x] journalisation structurée ;
- [x] endpoints `/health/live`, `/health/ready` et `/version` ;
- [x] premiers tests automatisés ;
- [x] Dockerfile et stack Compose ;
- [ ] tests locaux validés ;
- [ ] construction de l'image sur le NAS ;
- [ ] healthcheck Docker validé ;
- [ ] accès local sur `127.0.0.1` validé ;
- [ ] intégration au reverse proxy Synology ;
- [ ] documentation opérationnelle finalisée.

## Contraintes

- aucun secret dans Git ;
- aucune exposition directe sur Internet ;
- conteneur non-root ;
- système de fichiers en lecture seule ;
- limite mémoire et pondération CPU compatibles DSM ;
- aucune base de données sans besoin démontré.
