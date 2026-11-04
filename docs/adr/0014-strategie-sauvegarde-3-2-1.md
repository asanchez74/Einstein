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

### Domotique KNX du DS212j

Le DS212j (`192.168.1.4`, DSM 6.2.4 sans mises à jour) fait tourner `eibd` et
`linknx` (interface KNX-USB) et l'application web `eib`. Sa configuration est
copiée vers `homes/tonio/Sauvegardes/ds212j/` sur le DS918+ par
`scripts/pull-ds212j-config.sh` (rsync sur SSH, sans suppression), où les
instantanés de `homes`, Swiss Backup et Glacier la protègent. Clé SSH dédiée
`~/.ssh/ds212j_backup_ed25519` du compte tonio sur le DS918+, autorisée sur le
DS212j uniquement depuis `192.168.1.3`, sans terminal ni redirection. Tâche
planifiée DSM quotidienne à 23:30, utilisateur tonio. Première copie manuelle
le 2 novembre 2026 (7 149 fichiers).

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

### Calendrier de nuit

Après l'[incident du 4 novembre 2026](../incidents/2026-11-04-saturation-perte-ecritures.md),
les tâches lourdes ne démarrent plus en même temps :

| Heure | Tâche |
|---|---|
| 00:00 | instantanés quotidiens |
| 00:30 | Swiss Backup — NAS (incrémentale) |
| 01:00 | vidage des corbeilles |
| 02:00 | Glacier : Documents (lundi), Homes et Docker (mardi), Photo (mercredi), PhotoBAK (jeudi) |
| 03:00 → 03:30 | Hyper Backup locales toutes les 10 min : MailServerPlus, MariaDB, WebStation, Backups (tâche Notes supprimée le 4 novembre 2026 : Note Station ne contient aucune note) |
| 04:00 | Music Glacier (dimanche) |
| 04:15 | DS212j local — NAS |
| 04:30 | Backups et web_packages Glacier (dimanche) |
| samedi 21:30 | vérification d'intégrité Swiss Backup (2 h au plus) |

Mises à jour automatiques des paquets en notification seulement. Nettoyage des
données trimestriel, le premier samedi à 09:00. Un seul premier envoi long à la
fois.

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

Tâche Hyper Backup « Swiss Backup — NAS » : OpenStack Swift
(`swiss-backup02.infomaniak.com`, Keystone v3, utilisateur `SBI-AS579568`,
projet `sb_project_SBI-AS579568` et domaine `default` renseignés en `name`),
conteneur `default`, chiffrement côté client, compression, quotidienne à 00:30,
vérification d'intégrité le samedi à 21:30 limitée à 2 h (pour ne pas chevaucher
la sauvegarde de 00:30), conservation personnalisée (1 version par heure sur
1 jour, par jour sur 1 mois, par semaine sur 3 mois, puis par mois ; 256 versions
au plus). Dossiers : Backups, docker, Documents, homes, Scan, web, web_packages
(~390 Go hors instantanés et corbeilles). Applications : toutes **sauf Synology
Drive Server**. Première sauvegarde réussie le 2 novembre 2026 à 21:23 :
353,62 Go sur la cible.

**Piège : Synology Drive Server.** Cocher cette application dans Hyper Backup
ajoute les dossiers partagés où Drive est activé (Documents, Scan, homes et
**Video**), même s'ils sont décochés dans l'onglet Dossiers. La première tâche,
créée le même jour, a ainsi tenté d'envoyer 2,33 To et s'est arrêtée sur le
quota (`413 Upload exceeds quota`) après 936 Go, sans version exploitable.
Supprimer la tâche dans Hyper Backup n'a effacé que son cache local, pas les
données chez Infomaniak : l'appareil Swift (`SBI-AS605250`) a été supprimé et
recréé depuis le Manager. Avant de valider une tâche, vérifier la colonne
« Dossier partagé » de l'onglet Application.

Mesurer les tailles avec `du --exclude='#snapshot' --exclude='#recycle'` :
lorsque `#snapshot` est visible, `du` compte chaque instantané comme une copie
complète.

Tâche Hyper Backup « DS212j local — NAS » vers le dossier `SauvegardeDS918` du
DS212j (serveur rsync, compte `hb-ds918`) : même périmètre de dossiers et
d'applications que Swiss Backup, sans Synology Drive Server. Music, Photo,
PhotoBAK et Videos Personnelles en ont été retirés le 2 novembre 2026 : ils
restent protégés par le NAS et Glacier.

## Conséquences

- Coût récurrent d'environ CHF 6 par mois et un disque USB à acheter.
- Premier envoi de quelques heures (fibre 1 Gb/s).
- Rotation et contrôle du disque USB à intégrer à la routine (mensuelle).
- Glacier Backup repose sur l'ancien service Amazon Glacier à coffres, fermé aux
  nouveaux clients depuis le 15 décembre 2025 ; les clients existants gardent
  l'accès, sans migration obligatoire. La tâche Music (créée le 2 novembre 2026)
  est à Francfort, les autres en US East.
- Stockage Glacier : ~0,0036 $/Go/mois en US East, ~0,004 à 0,0045 $ à
  Francfort (non confirmé), soit 1 à 2 $/mois d'écart pour ~2 To. Durée
  minimale de facturation de 90 jours : ne pas déplacer les archives envoyées en
  novembre 2026 avant février 2027.

## Réévaluation (fin janvier 2027)

À la fin de l'essai Swiss Backup :

- confirmer le renouvellement annuel Swiss Backup ;
- décider du rôle de Glacier : passer Swiss Backup à 2 To pour y mettre PhotoBAK
  et les vidéos personnelles (~CHF 4/mois de plus) puis retirer Glacier, ou
  garder Glacier comme archive froide et la regrouper à Francfort.

## Suite

- Acheter et mettre en place le disque USB (tâche Hyper Backup locale).
- Exporter le fichier de clé `.pem` de la tâche Swiss Backup vers SafeInCloud.
- Tester une restauration depuis Swiss Backup avec Hyper Backup Explorer.
- Vérifier la première sauvegarde « DS212j local — NAS ».
- Contrôler les tâches Glacier Backup (réinstallées le 1er novembre 2026) et
  créer la tâche Music.
- Vérifier l'apparition des instantanés horaires de Documents et homes.
- Rédiger la procédure de reconstruction du NAS (ordre DSM, Hyper Backup,
  paquets, Docker, stacks Einstein), conservée aussi hors du NAS.
