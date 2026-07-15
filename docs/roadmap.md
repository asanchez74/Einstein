# Roadmap

## Sprint 1 — Infrastructure

- [x] Git
- [x] VS Code
- [x] Documentation MkDocs
- [x] OpenVPN
- [x] SSH
- [x] VS Code Remote SSH

## Sprint 2 — Plateforme

- [ ] Docker
- [ ] Traefik
- [ ] PostgreSQL
- [ ] Qdrant

## Sprint 3 — Einstein Core

- [ ] CLI
- [ ] Configuration
- [ ] Journalisation

## Sprint 4 — Einstein Maison

- [ ] Huawei
- [ ] Homebridge
- [ ] Automatisations

<!-- BEGIN SPRINT_2_STATUS -->
## Sprint 2 — Socle Docker reproductible

**Statut : terminé le 15 juillet 2026.**

Principaux résultats :

- dépôt GitHub privé et Deploy key NAS en lecture seule ;
- séparation du dépôt et des données persistantes ;
- conventions Docker Compose ;
- modèle de service sécurisé ;
- service `smoke-test` validé ;
- limites mémoire et pondération CPU compatibles DSM ;
- healthchecks, logs rotatifs et ports locaux ;
- scripts standardisés d’exploitation ;
- sauvegardes horodatées avec manifeste et SHA-256 ;
- documentation MkDocs et ADR complétés.

### Prochaine étape

**Sprint 3 — Socle applicatif Einstein**

Objectifs pressentis :

- API centrale légère ;
- configuration commune ;
- gestion des secrets ;
- persistance applicative ;
- endpoints de santé ;
- préparation des agents, workflows et fournisseurs de modèles.
<!-- END SPRINT_2_STATUS -->
