# Sprint 4 — Premier inventaire Einstein Maison

## Statut

**Terminé — clôture documentaire le 17 octobre 2026.**

Déployé au commit `a15e636`. Les preuves ci-dessous distinguent les contrôles
successifs et leurs limites. La restauration est validée par extraction et
lecture applicative en répertoire temporaire, sans remplacement en production.

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
Le catalogue d’exemple est déployé. La santé, les accès HTTPS et le test de
restauration en répertoire temporaire sont confirmés dans les sections suivantes. Aucune nouvelle
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

## Déploiement NAS du 17 octobre 2026

Le clone NAS a été mis à jour par fast-forward au commit
`a15e6364f12131137cf7786ddd4b45b47cdbed86`.
Les sorties terminal transmises par le propriétaire confirment :

- construction réussie avec Python `3.14.6-slim-bookworm` ;
- image `einstein-core:0.1.0`, identifiant
  `sha256:b61a0499f0f8aec07e846cf3b9e5a4b98ccc3be37b61ce91c6a72082864649f7` ;
- validation du fichier monté via un conteneur temporaire :
  `Inventaire valide : 3 équipement(s)` ;
- déploiement par `stack-up.sh einstein-core` réussi ;
- liste HTTP locale contenant `fritzbox`, `nas`, `pihole`, dans cet ordre ;
- détail HTTP local de `nas` conforme au catalogue.

Le healthcheck affichait encore `starting` lors des premiers relevés.
Les sections suivantes consignent les vérifications healthy, HTTPS et sauvegarde.

## Contrôles complémentaires après déploiement

Le propriétaire transmet ensuite les résultats suivants :

| Contrôle | Résultat |
|---|---|
| Healthcheck Docker Einstein Core | `healthy` |
| HTTPS `/api/v1/maison/equipements` depuis le Mac | Liste conforme : `fritzbox`, `nas`, `pihole` |

Cette première sortie HTTPS ne précisait pas le mode de connexion du Mac.
La confirmation des accès LAN/VPN et du refus externe est consignée ci-dessous.

## Validation des accès à l'inventaire

Le propriétaire confirme que `/api/v1/maison/equipements` répond sur le LAN
et via VPN, et reçoit HTTP 403 depuis la connexion externe sans VPN.
La politique LAN/VPN autorisés, accès Internet refusé est donc vérifiée pour
cette route après déploiement. Le test de sauvegarde/restauration est décrit
dans la section suivante.

## Sauvegarde et restauration en répertoire temporaire

Le 17 octobre 2026 à 09:28:49 (Europe/Zurich), le propriétaire a exécuté
`backup-stack.sh einstein-core`. Les sorties confirment l'arrêt temporaire,
la création de l'archive et le redémarrage du service.

- Archive : `/volume1/docker/einstein/backups/einstein-core/einstein-core-20261017-092848.tar.gz`.
- Commit du manifeste : `a15e6364f12131137cf7786ddd4b45b47cdbed86`.
- Source : `/volume1/docker/einstein/data/einstein-core`.
- SHA-256 calculé et identique au manifeste :
  `4e8c731cb1dfcc791dbd6c2720dbc1a575721e78bfff8fb2197e44d27da87e0e`.
- Contenu inspecté : `einstein-core/equipements.json`.

L'archive a été extraite dans un répertoire temporaire sous
`/volume1/docker/einstein/tmp/core-restore.*`, avec permissions de lecture
pour l'UID/GID `10001:10001`. Un conteneur temporaire utilisant ce répertoire
sur `/inventory:ro` a retourné `Inventaire valide : 3 équipement(s)`.

Ce test valide l'extraction et la lecture du catalogue restauré avec le
validateur applicatif. Il n'a pas remplacé le catalogue actif et ne constitue
pas un test HTTP complet de l'application sur les données restaurées.
Le répertoire temporaire reste à nettoyer après vérification de son chemin.
Après sauvegarde, le propriétaire a confirmé `healthy` sur le NAS et une
réponse HTTPS contenant les trois équipements depuis le Mac.

## Bilan de clôture

- 29 tests locaux réussis, `compileall`, MkDocs strict et diff vérifiés.
- Construction et déploiement NAS identifiés par commit et empreinte d'image.
- Liste et détail validés localement ; liste validée en HTTPS LAN et VPN.
- Refus externe HTTP 403 confirmé sur la route de liste.
- Sauvegarde avec manifeste, empreinte vérifiée et catalogue extrait valide.
- Service healthy et inventaire accessible après sauvegarde.

Le RT2600ac reste exclu du catalogue tant que son rôle précis n'est pas
confirmé. Les fichiers temporaires de restauration sont à nettoyer après
vérification du chemin ; la copie externe des sauvegardes reste à organiser.
Aucune restauration complète en production ni tenue en charge n'est déclarée
validée. Les tâches Pi-hole reportées du Sprint 3 restent au suivi d'exploitation.
