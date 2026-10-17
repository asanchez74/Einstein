# Sprint 4 — Premier inventaire Einstein Maison

## Statut

**En cours — implémentation locale le 17 octobre 2026 ; NAS non déployé.**

## Objectif

Consulter depuis l'API les équipements connus de la maison et leur rôle,
sans scanner le réseau ni commander les appareils. Premier usage : retrouver
l'adresse et le rôle du NAS, des routeurs et de Pi-hole depuis une source
explicite et validée.

## Périmètre retenu

Un module Maison dans Einstein Core, avec un catalogue déclaratif JSON chargé
et validé au démarrage. Aucun nouveau service, aucune base de données et
aucune dépendance supplémentaire ne sont nécessaires pour ce périmètre.

Le catalogue contient uniquement des informations descriptives. Il ne
remplace ni le DHCP Synology ni les entrées DNS Pi-hole et ne les modifie pas.

| Champ | Règle |
|---|---|
| `id` | Identifiant stable, unique, en minuscules avec tirets |
| `name` | Nom lisible non vide |
| `category` | `nas`, `router` ou `dns` pour le premier catalogue |
| `address` | Adresse IP validée |
| `role` | Description non vide, sans secret |

Exemples connus : NAS DS918+ (`192.168.1.3`), FRITZ!Box (`192.168.1.1`),
Synology RT2600ac (`192.168.1.2`) et Pi-hole (`192.168.1.56`). Ne pas inventer
le rôle précis du RT2600ac dans la topologie : le faire confirmer avant de
renseigner cette description.

## Contrat HTTP

| Route | Résultat |
|---|---|
| `GET /api/v1/maison/equipements` | 200, liste ordonnée par identifiant ; liste vide autorisée |
| `GET /api/v1/maison/equipements/{id}` | 200, équipement trouvé ; 404 sinon |

Les deux routes retournent les mêmes champs. Aucun endpoint d'écriture,
filtrage, pagination ou accès réseau sortant n'est prévu à ce stade.
Les routes de santé et de version existantes sont conservées.

## Source et cycle de vie du catalogue

Fichier local hors Git prévu sur le NAS, sous
`/volume1/docker/einstein/data/einstein-core/equipements.json`, monté en
lecture seule. Un exemple sans secret est versionné pour le développement.
Le chemin est configuré par `EINSTEIN_MAISON_INVENTORY_PATH`.

Cette implémentation fait évoluer le Core sans état : le fichier externe devient
une donnée de configuration à sauvegarder. Documenter cette évolution et sa
restauration avant déploiement. Le choix est décrit dans l’ADR-0006 ; les ADR existantes sont conservées.

Le fichier est chargé une fois au démarrage, sans surveillance automatique.
Un redémarrage applique une mise à jour. Un fichier absent, illisible,
invalide ou contenant des identifiants dupliqués empêche le démarrage avec
une erreur explicite, sans afficher tout son contenu dans les logs.

## Lots et critères d'acceptation

1. Confirmer le modèle et le contrat HTTP avec un catalogue d'exemple, puis
   documenter le stockage retenu et ses conséquences d'exploitation.
2. Implémenter les modèles et le chargement JSON dans un module Maison,
   avec tests de données valides, invalides et identifiants dupliqués.
3. Ajouter liste et détail avec tests HTTP : ordre stable, catalogue vide,
   équipement trouvé et 404. Les tests ne dépendent ni du NAS ni du réseau.
4. Brancher le chargement au cycle de vie, tester les échecs de démarrage
   et vérifier les endpoints existants avec une configuration de test isolée.
5. Préparer le montage en lecture seule, les permissions UID/GID `10001:10001`,
   la sauvegarde du catalogue et la procédure de mise à jour.
6. Exécuter les tests, `compileall`, le build MkDocs strict et les contrôles
   de diff ; déployer un commit identifié, contrôler les routes et la santé
   du service sur le NAS, puis vérifier LAN/VPN et refus externe.

Le sprint est terminé lorsque ces contrôles sont consignés et que l'inventaire
réel est consultable par le chemin HTTPS existant, sans privilège supplémentaire
et sans commande sur les équipements.

## Hors périmètre

- intégration LLM, agents, recherche vectorielle ;
- découverte automatique, synchronisation DHCP/DNS ou suivi de disponibilité ;
- commandes sur les équipements et interface graphique ;
- historique, écriture concurrente et base de données.

Les tâches d'exploitation Pi-hole reportées du Sprint 3 restent suivies dans
sa documentation ; elles ne sont pas déclarées terminées par ce cadrage.

## Avancement de l'implémentation

Modèles, chargement JSON, unicité, instantané, routes liste/détail et erreurs
404 sont implémentés. Les tests existants et les tests Maison passent
localement (29 tests). Le montage Compose en lecture seule, le catalogue
d'exemple et les procédures de sauvegarde/restauration sont préparés.
Voir l'[ADR-0006](../adr/0006-inventaire-json-maison.md).

Le RT2600ac n'est pas inclus dans l'exemple : son rôle attend confirmation.
La validation Docker effective, le catalogue réel, la sauvegarde/restauration
et le déploiement NAS restent à effectuer avant clôture. Aucune nouvelle
infrastructure ni dépendance n'a été ajoutée.

## Validation avant déploiement

La commande `python -m einstein_core.maison <catalogue.json>` valide un
catalogue sans démarrer le serveur ni modifier le fichier. Elle retourne 0
si valide, 1 sinon, sans reproduire les données invalides dans les erreurs.
Les adresses IP doivent être des chaînes : les valeurs numériques et les
booléens sont rejetés, sans conversion implicite en IPv4.

La suite vérifie aussi les permissions refusées et l'isolation de deux
applications utilisant des catalogues distincts. Les 29 tests passent
localement ; cette vérification ne constitue pas une validation Docker/NAS.
