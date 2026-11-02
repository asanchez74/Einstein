# ADR-0014 — Stratégie de sauvegarde 3-2-1

- **Statut :** proposé
- **Date :** 2 novembre 2026

## Contexte

Le NAS DS918+ (SHR, 4 × 3,6 To, 6,7 To utilisés) protège ses données par :

- le RAID SHR, qui tolère la panne d'un disque mais réplique aussitôt une
  suppression ou un chiffrement ;
- des instantanés Snapshot Replication quotidiens, sur le même volume ;
- Hyper Backup vers le dossier `Backups`, sur le même NAS ;
- Glacier Backup (AWS, région N. Virginia), avec les tâches « Homes Glacier et
  Docker Backup » (homes, docker), « Documents Glacier Backup » (Documents,
  Scan), « Photo Glacier Backup », « PhotoBAK Glacier Backup » (PhotoBAK,
  Video/Videos Personnelles) et « Backups et web_packages Glacier ». Ces tâches
  ont été modifiées le 1er novembre 2026 ; leur réussite après l'incident reste
  à confirmer.

L'incident du [1er novembre 2026](../incidents/2026-11-01-suppression-volume1.md)
a été réparé grâce aux instantanés. Une perte du volume ou du NAS (panne,
incendie, vol, rançongiciel, erreur d'administration) emporterait en revanche
les données, les instantanés et les sauvegardes Hyper Backup.

Tailles relevées le 2 novembre 2026 (Go, hors corbeilles) : homes 247, Photo 84,
Documents 60, MailPlus 5 (+22 dans `@MailPlus-Server`), docker, web, Scan ~10,
Music 79, PhotoBAK 937, Video 1 613, TimeMachine 1 761, Backups 46,
surveillance et Downloads 11.

## Décision

Appliquer la règle **3-2-1** : trois copies, deux supports, une copie hors site.

| Données | Hors site | Copie locale séparée |
|---|---|---|
| homes, Documents, docker (données et secrets Einstein), web, web_packages, Scan, Backups (sauvegardes Hyper Backup locales, dont `DSM_Parametres`), toutes les applications, configuration système | **Infomaniak Swiss Backup** via Hyper Backup (Swift), ~0,4 To | disque USB, Hyper Backup |
| PhotoBAK (toutes les photos), Video/Videos Personnelles | **Glacier Backup** (existant) ; Photos iCloud n'est qu'une synchronisation | facultatif |
| Photo, Music | **Glacier Backup** (tâche Music à créer) | — |
| TimeMachine, surveillance, Downloads | exclus | — |
| Messagerie et contacts | chez Infomaniak après migration ([ADR-0013](0013-migration-messagerie-infomaniak.md)) | exportation périodique des contacts |

**Swiss Backup est la sauvegarde hors site principale** (restauration
immédiate, sans frais, versionnée, en Suisse). **Glacier Backup reste une
archive froide** de dernier recours chez un second fournisseur : les tâches
existantes sont conservées, y compris pour les données aussi envoyées à Swiss
Backup.

Règles :

- **Chiffrement** côté NAS dans Hyper Backup. Mot de passe de chiffrement,
  identifiants Swift et contenu du fichier de clé `.pem` dans SafeInCloud
  (coffre synchronisé par Dropbox, indépendant du NAS).
- **Fiche papier de secours**, hors du NAS et hors ligne : mot de passe maître
  SafeInCloud et codes de secours Dropbox. Tout le reste se retrouve dans le
  coffre.
- **Versions** Hyper Backup : une par heure sur 1 jour, par jour sur 1 mois, par
  semaine sur 3 mois, puis par mois (256 au plus).
- **Disque USB débranché** entre deux sauvegardes, **prioritaire** : seule copie
  hors d'atteinte d'un compte administrateur compromis ou d'un rançongiciel.
  Swiss Backup n'offre pas d'immutabilité en Swift/S3 (réservée aux plans
  Acronis) et le DS918+ ne propose pas d'instantanés immuables (seulement
  « Verrouiller », qui empêche la suppression automatique mais pas une
  suppression par un administrateur).
- **Test de restauration** trimestriel d'un dossier depuis Swiss Backup, avec
  Hyper Backup Explorer sur le Mac ; notifications d'échec activées.

### Instantanés (Snapshot Replication)

Première ligne de défense contre les erreurs, sur le même volume. Politique
appliquée le 2 novembre 2026 (conservation avancée : tous les instantanés
pendant 1 jour, derniers 5 toujours conservés, dernier de l'année pendant 1 an) :

| Groupe | Dossiers | Planification | Heure / jour / semaine / mois | `#snapshot` visible |
|---|---|---|---|---|
| Fichiers de travail | Documents, homes | toutes les heures de 07:00 à 23:00 | 24 h / 14 j / 8 sem. / 6 mois | oui |
| Critiques peu modifiés | PhotoBAK, docker | quotidienne à 00:00 | 24 h / 14 j / 8 sem. / 6 mois | non |
| Autres | Backups, MailPlus, Photo, Music, Video, Scan, web, web_packages, Downloads, Rapports Synology | quotidienne à 00:00 | 24 h / 14 j / 4 sem. / 3 mois | non |
| Sans instantanés | TimeMachine, surveillance | — | — | — |

`@appstore` et `@database` ne sont pas des dossiers partagés et n'ont pas
d'instantanés ; la sauvegarde Swiss Backup des applications et de la
configuration système couvre ce manque. Snapshot Replication ne réplique que
vers un autre Synology : pas de réplication tant qu'aucun second NAS n'existe.

## Alternatives évaluées

Coût de stockage mensuel indicatif pour ~0,5 To (sources tierces, à confirmer) :

| Solution | Coût | Remarques |
|---|---|---|
| **Infomaniak Swiss Backup** | ~5 à 9 € | Suisse, guide Hyper Backup officiel, pas de frais de restauration annoncés |
| Exoscale (S3, Suisse) | ~10 € | sortie ~0,02 $/Go |
| AWS S3 Standard / Standard-IA | ~13 $ / ~7 $ | sortie ~0,09 $/Go ; Hyper Backup n'écrit pas directement en Glacier ou Deep Archive |
| Second NAS chez un proche | achat unique | indépendant et immuable possible, mais maintenance et dépendance à l'hôte |

Tarif officiel Swiss Backup relevé le 2 novembre 2026 (paiement annuel, -10 %) :
capacité 1 To CHF 4,18/mois et 1 appareil « Sauvegarde Cloud » CHF 1,84/mois,
soit **CHF 6,02/mois** (environ CHF 72/an), TVA probablement en sus.
Commandé le 2 novembre 2026 (BK-711964-1, 1 To, 1 emplacement Swift/S3/SFTP),
avec un essai gratuit de 90 jours jusqu'à fin janvier 2027, puis renouvellement
annuel.

Tâche Hyper Backup créée le 2 novembre 2026 : « Swiss Backup — NAS », OpenStack
Swift (`swiss-backup02.infomaniak.com`, Keystone v3, projet et domaine renseignés
en `name`), conteneur `nas-chantevigne`, chiffrement côté client, compression,
quotidienne à 00:30, vérification d'intégrité le samedi à 21:30, conservation
personnalisée (1 version par heure sur 1 jour, par jour sur 1 mois, par semaine
sur 3 mois, puis par mois ; 256 versions au plus).

## Conséquences

- Coût récurrent d'environ CHF 6 par mois et un disque USB à acheter.
- Premier envoi de quelques heures (fibre 1 Gb/s).
- Rotation et contrôle du disque USB à intégrer à la routine (mensuelle).
- Glacier Backup repose sur l'ancien service Amazon Glacier à coffres : vérifier
  sa pérennité et ses coûts de restauration, prévoir une migration si
  nécessaire.

## Suite

- Acheter et mettre en place le disque USB (tâche Hyper Backup locale).
- Exporter le fichier de clé `.pem` de la tâche Swiss Backup vers SafeInCloud.
- Vérifier la première sauvegarde Swiss Backup, puis tester une restauration
  avec Hyper Backup Explorer.
- Contrôler les tâches Glacier Backup (réinstallées le 1er novembre 2026) et
  créer la tâche Music.
- Vérifier l'apparition des instantanés horaires de Documents et homes.
- Rédiger la procédure de reconstruction du NAS (ordre DSM, Hyper Backup,
  paquets, Docker, stacks Einstein), conservée aussi hors du NAS.
