# ADR-0002 — Séparation du code et des données persistantes

- **Statut :** accepté
- **Date :** 15 juillet 2026

## Contexte

Einstein doit pouvoir être reconstruit depuis Git tout en conservant les
données persistantes propres au NAS.

Les bases de données, journaux, secrets et fichiers générés ne doivent pas être
mélangés avec les sources versionnées.

## Décision

Le dépôt Git est stocké sur le NAS dans :

```text
/var/services/homes/tonio/Development/Einstein
```

Les données d'exécution sont stockées séparément dans :

```text
/volume1/docker/einstein
```

avec l'organisation suivante :

```text
/volume1/docker/einstein/
├── data/
├── logs/
├── secrets/
├── backups/
└── tmp/
```

Les secrets et fichiers `.env` réels ne sont jamais enregistrés dans Git.

## Conséquences positives

- dépôt Git léger et reproductible ;
- persistance indépendante du cycle de vie des conteneurs ;
- sauvegardes ciblées ;
- secrets conservés hors de GitHub ;
- reconstruction possible depuis les fichiers Compose.

## Conséquences négatives

- préparation initiale des dossiers du NAS ;
- gestion séparée des sauvegardes ;
- contrôle des permissions nécessaire pour chaque service.
