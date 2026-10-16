# Roadmap

Cette roadmap décrit l'évolution progressive de la plateforme Einstein.

Les choix techniques peuvent évoluer au fil des validations. Toute décision
structurante est documentée dans une ADR.

## Sprint 1 — Infrastructure

**Statut : terminé**

- [x] Initialisation du dépôt Git
- [x] Développement avec VS Code sur le Mac
- [x] Documentation avec MkDocs
- [x] Accès distant par OpenVPN
- [x] Accès SSH au Synology
- [x] VS Code Remote SSH
- [x] Roadmap et premières décisions d'architecture

## Sprint 2 — Socle Docker reproductible

**Statut : terminé et validé**

- [x] Dépôt GitHub privé comme référence centrale
- [x] Deploy key GitHub en lecture seule sur le NAS
- [x] Séparation du code et des données persistantes
- [x] Arborescence `/volume1/docker/einstein`
- [x] Conventions Docker Compose
- [x] Modèle Compose réutilisable
- [x] Limites mémoire adaptées au DS918+
- [x] Pondération CPU avec `cpu_shares`
- [x] Conteneur exécuté sans privilèges inutiles
- [x] Système de fichiers du conteneur en lecture seule
- [x] Healthcheck
- [x] Publication des ports d'administration sur `127.0.0.1`
- [x] Rotation des journaux
- [x] Service de validation `smoke-test`
- [x] Scripts standardisés d'exploitation
- [x] Sauvegarde avec manifeste et empreinte SHA-256
- [x] Cycle complet de déploiement et de restauration validé
- [x] Documentation et ADR du socle Docker

Les composants Traefik, PostgreSQL et Qdrant ne font pas partie du Sprint 2.
Ils ne seront ajoutés que lorsqu'un besoin applicatif réel le justifiera.

## Sprint 3 — Socle applicatif Einstein

**Statut : en cours**

État des livrables :

- [x] Définir l'architecture applicative (ADR-0005)
- [x] Choisir le socle technique de l'API Einstein (Python 3.14 et FastAPI)
- [x] Créer un premier service applicatif léger
- [x] Mettre en place la configuration par environnement
- [ ] Définir la gestion des secrets applicatifs (aucun secret requis actuellement)
- [x] Ajouter les endpoints de santé et de version
- [x] Mettre en place les tests automatisés et les valider localement
- [x] Préparer l'accès par le reverse proxy Synology (validation NAS consignée au Sprint 3)
- [x] Documenter la décision d'architecture applicative
- [ ] Finaliser la documentation opérationnelle
- [ ] Consolider les preuves de validation NAS avec date et commit

Les tests locaux ont été vérifiés le 16 octobre 2026 : 5 tests réussis sous
Python 3.14.4. Les validations NAS déjà déclarées n'ont pas été rejouées lors
de cet audit local. Le sprint reste ouvert ; son état détaillé figure dans
[Sprint 3 — Socle applicatif](sprints/sprint-3-socle-applicatif.md).

## Étapes ultérieures

Les étapes suivantes seront planifiées après validation du socle applicatif :

- intégration des fournisseurs de modèles IA ;
- orchestration des agents ;
- mémoire et recherche documentaire ;
- workflows ;
- interface utilisateur ;
- observabilité ;
- automatisation des sauvegardes ;
- éventuelle base PostgreSQL ;
- éventuelle base vectorielle, uniquement si le besoin est démontré.
