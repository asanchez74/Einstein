# ADR-0014 — Stratégie de sauvegarde 3-2-1

- **Statut :** proposé
- **Date :** 2 novembre 2026

## Contexte

Le NAS DS918+ (SHR, 4 × 3,6 To, 6,7 To utilisés) protège ses données par :

- le RAID SHR, qui tolère la panne d'un disque mais réplique aussitôt une
  suppression ou un chiffrement ;
- des instantanés Snapshot Replication quotidiens, sur le même volume ;
- Hyper Backup vers le dossier `Backups`, sur le même NAS ;
- Glacier Backup (AWS) pour `PhotoBAK` et `Video`.

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
| homes, Photo, Documents, docker (données et secrets Einstein), web, Scan, Music, configuration DSM et paquets | **Infomaniak Swiss Backup** via Hyper Backup (Swift), ~0,5 To | disque USB, Hyper Backup |
| PhotoBAK, Video | **Glacier Backup** (existant) | facultatif |
| TimeMachine, surveillance, Downloads, Backups | exclus | — |
| Messagerie et contacts | chez Infomaniak après migration ([ADR-0013](0013-migration-messagerie-infomaniak.md)) | exportation périodique des contacts |

Règles :

- **Chiffrement** côté NAS dans Hyper Backup ; clé conservée hors du NAS
  (gestionnaire de mots de passe et copie papier).
- **Versions** Hyper Backup avec rotation intelligente (par exemple quotidienne
  sur 30 jours, hebdomadaire sur 3 mois, mensuelle sur 12 mois).
- **Disque USB débranché** entre deux sauvegardes : il compense l'absence
  d'immutabilité de Swiss Backup en Swift/S3 (immutabilité réservée aux plans
  Acronis).
- **Instantanés immuables** à étudier dans Snapshot Replication (DSM 7.2), contre
  la suppression des instantanés par un compte compromis.
- **Test de restauration** trimestriel d'un dossier depuis Swiss Backup, avec
  Hyper Backup Explorer sur le Mac ; notifications d'échec activées.

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

## Conséquences

- Coût récurrent d'environ CHF 6 par mois et un disque USB à acheter.
- Premier envoi de quelques heures (fibre 1 Gb/s).
- Rotation et contrôle du disque USB à intégrer à la routine (mensuelle).
- Glacier Backup repose sur l'ancien service Amazon Glacier à coffres : vérifier
  sa pérennité et ses coûts de restauration, prévoir une migration si
  nécessaire.

## Suite

- Contrôler les tâches Glacier Backup (réinstallées le 1er novembre 2026).
- Rédiger la procédure de reconstruction du NAS (ordre DSM, Hyper Backup,
  paquets, Docker, stacks Einstein), conservée aussi hors du NAS.
