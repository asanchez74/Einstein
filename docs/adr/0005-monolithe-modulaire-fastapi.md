# ADR-0005 — Monolithe modulaire Python avec FastAPI

- **Statut :** accepté
- **Date :** 23 juillet 2026

## Contexte

Einstein doit disposer d'un premier service applicatif léger, testable et
évolutif sur un Synology DS918+ disposant de ressources limitées.

L'installation immédiate de plusieurs services distribués augmenterait la
complexité d'exploitation avant que leurs besoins soient démontrés.

## Décision

Le socle applicatif prend la forme d'un monolithe modulaire nommé
`einstein-core`, développé en Python avec FastAPI.

Le service démarre avec un seul processus Uvicorn et ne dépend initialement
d'aucune base de données.

## Raisons

- faible consommation de ressources ;
- typage et validation des données ;
- documentation OpenAPI automatique ;
- tests HTTP simples ;
- possibilité d'extraire ultérieurement un module en service séparé.

## Éléments différés

PostgreSQL, Qdrant et un proxy Docker dédié ne seront introduits que si un
besoin fonctionnel ou opérationnel mesurable le justifie.
