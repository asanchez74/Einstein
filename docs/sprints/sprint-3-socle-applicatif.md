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
Le README du service rapporte également un accès HTTPS par le reverse proxy,
limité au VPN, et un refus d'accès hors VPN.

Avant la clôture, compléter la procédure opérationnelle et consigner une
validation NAS datée, associée au commit déployé : construction de l'image,
healthcheck, endpoints locaux et via HTTPS/VPN, refus hors VPN, redémarrage
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
