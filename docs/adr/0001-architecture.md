# ADR-0001 : Accès distant sécurisé

## Statut

Accepté

## Contexte

Le développement d'Einstein doit être possible depuis n'importe où tout en évitant d'exposer les services internes directement sur Internet.

## Décision

Tous les accès d'administration passent par :

- OpenVPN Synology
- SSH

Les applications d'Einstein ne seront pas exposées directement.

## Conséquences

- Administration centralisée.
- Sécurité renforcée.
- Aucun accès SSH public.
- Développement possible depuis VS Code via Remote SSH.