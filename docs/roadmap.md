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

Objectifs prévisionnels :

- [ ] Définir l'architecture applicative
- [ ] Choisir le socle technique de l'API Einstein
- [ ] Créer un premier service applicatif léger
- [ ] Mettre en place la configuration par environnement
- [ ] Définir la gestion des secrets
- [ ] Ajouter un endpoint de santé
- [ ] Mettre en place les tests automatisés
- [ ] Préparer l'accès par le reverse proxy Synology
- [ ] Documenter les nouvelles décisions d'architecture

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
