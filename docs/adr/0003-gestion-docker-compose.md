# ADR-0003 — Gestion des services avec Docker Compose

- **Statut :** accepté
- **Date :** 15 juillet 2026

## Contexte

Einstein nécessite une configuration déclarative, versionnée et reproductible.

Sur le Synology, le socket Docker appartient à `root:root` et son accès
nécessite actuellement des privilèges élevés.

## Décision

Les services Einstein sont définis avec Docker Compose et exploités depuis la
ligne de commande.

Les commandes Docker sont exécutées avec `sudo`.

Les permissions du socket Docker ne sont pas modifiées et aucun groupe
`docker` supplémentaire n'est créé.

Portainer et les systèmes de mise à jour automatique ne sont pas installés
pendant la construction du socle.

## Raisons

- Docker Compose est déclaratif et versionnable ;
- les changements sont traçables dans Git ;
- les configurations peuvent être validées avant le déploiement ;
- les mises à jour restent contrôlées ;
- aucune interface d'administration Docker supplémentaire n'est exposée.

## Conséquences positives

- déploiements reproductibles ;
- historique des changements ;
- surface d'administration limitée ;
- mises à jour préparées et documentées.

## Conséquences négatives

- les opérations nécessitent une connexion SSH ;
- le mot de passe `sudo` peut être demandé ;
- les mises à jour nécessitent une intervention volontaire.
