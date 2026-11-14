# Incident du 4 novembre 2026 — saturation du NAS et perte d'écritures

- **Gravité :** majeure (données récentes perdues, messagerie et Drive indisponibles)
- **Durée :** 3 novembre ~14:40 (premiers symptômes) → 4 novembre 18:15 (dernières réparations)
- **Cause :** NAS saturé (disque et mémoire) pendant les premiers envois de sauvegarde,
  puis arrêt par l'interrupteur alors que les écritures n'étaient pas sur disque
- **Perte définitive :** aucune ; les deux mails de Mimi (06:16 et 07:08) ont
  été récupérés (confirmé le 14 novembre 2026)

## Résumé

Pendant la mise en place de la [stratégie de sauvegarde](../adr/0014-strategie-sauvegarde-3-2-1.md),
plusieurs premiers envois longs tournaient en même temps que les tâches de nuit
habituelles. Le NAS a saturé : charge ~11 dont ~10 d'attente disque, 2,9 Go de
swap sur 8 Go de mémoire. Docker ne lançait plus de commande dans les conteneurs
et les écritures ne parvenaient plus au disque.

Le 4 novembre vers 08:44, le NAS a été arrêté par l'interrupteur. Les fichiers
écrits entre minuit et l'arrêt existaient encore après redémarrage, mais vides.

## Chronologie

| Heure | Événement |
|---|---|
| 2 nov. ~21:45 | Premier envoi « DS212j local — NAS » (~20 h à 5,7 Mo/s), envois Glacier en cours |
| 3 nov. ~14:40 | `docker exec pihole` bloqué : la synchronisation DHCP ne se termine plus |
| 3 nov. → 4 nov. | Toutes les 5 min, notification DSM « tâche ignorée car déjà en cours » |
| 4 nov. 00:00 | 13 instantanés quotidiens, puis Swiss Backup (00:30), sauvegardes locales (03:00) |
| 4 nov. 00:58 | Réécriture des 16 128 fichiers WordPress (lisbonne2027.ch) |
| 4 nov. 07:32 | `git pull` du dépôt Einstein sur le NAS |
| 4 nov. 07:39 | Mise à jour automatique de Synology Drive Server 4.0.4 |
| 4 nov. ~08:44 | Arrêt par l'interrupteur, redémarrage |
| 4 nov. 08:48–08:55 | Container Manager relancé ; `docker exec` de nouveau fonctionnel |
| 4 nov. 09:10 | Drive Server réinstallé manuellement |
| 4 nov. 17:15–18:10 | Diagnostic de la messagerie, suppression des messages vides |
| 4 nov. 17:40 | Dépôt Einstein du NAS recloné |
| 4 nov. 18:13 | `web_packages` restauré depuis l'instantané de 00:00 |

## Dégâts et réparations

| Élément | Effet | Réparation |
|---|---|---|
| Synology Drive Server | 2 955 fichiers sur 2 960 vides ; paquet arrêté (`stopped_by_dep_limit`, `Failed to get app portal config`) | installation manuelle du même `.spk` 4.0.4-27894 |
| Messagerie tonio | 198 mails vides (194 corbeille, 2 envoyés, 1 réception, 1 indésirable) ; iPhone et iPad en « erreur de compte » | `doveadm expunge` par UID ; 3 messages à remettre depuis le Mac (copie dans `~/Sauvegarde-Mails-20261104`) |
| Messagerie mimi | 4 mails vides (2 réception reçus à 06:16 et 07:08, 2 corbeille) | `doveadm expunge` par UID ; messages récupérés (confirmé le 14 novembre 2026) |
| WordPress (`web_packages`) | 16 113 fichiers vides | restauration de l'instantané du 4 novembre 00:00:05 |
| Dépôt Einstein du NAS | objets git et 4 fichiers du `git pull` vides ; script DHCP vide | nouveau clone, `.env` recopiés, ancien dossier renommé `Einstein.abime-20261104` |
| Sauvegarde Homebridge 04:00 | vide | refaite la nuit suivante |
| Synology Contacts | 757 contacts au lieu de 1 488 (constaté le 6 novembre, perte probablement liée à l'incident) | carnet complet récupéré depuis la copie locale du Mac et passé dans iCloud ([ADR-0013](../adr/0013-migration-messagerie-infomaniak.md)) |
| Documents, homes (hors dépôt), Photo, PhotoBAK, Music, Backups | intacts | — |

Le matériel est sain : quatre disques et cache SSD (RAID 1, lecture-écriture).

## Points techniques

**Docker bloqué.** `sudo timeout 10 docker exec pihole true; echo $?` renvoie
`124` : le démon ne lance plus de commande dans aucun conteneur. Les conteneurs et
le DNS continuent de fonctionner. Redémarrer Container Manager (courte coupure
DNS). Le script de synchronisation DHCP coupe désormais chaque appel `docker`
après 30 s.

**Fichiers vides.** Pour mesurer les dégâts sur une période :

```bash
find "<dossier>" -path "*#snapshot*" -prune -o -type f -size 0 \
    -newermt "<début>" ! -newermt "<fin>" -print
```

**Messages IMAP vides.** Dovecot signale `Broken physical size` ou `Cached message
size larger than expected (N > 0)`. Un client iOS qui tombe dessus affiche
« erreur de compte » ou « le serveur ne répond pas » ; un Mac qui a déjà les
messages en cache semble fonctionner. Supprimer un tel message depuis un client
échoue (le déplacement vers la corbeille doit le lire). Les supprimer côté serveur
par UID, après aperçu :

```bash
D=/var/packages/MailPlus-Server/target/bin/doveadm
sudo $D search  -u <compte> mailbox <dossier> uid <liste> | wc -l
sudo $D expunge -u <compte> mailbox <dossier> uid <liste>
```

Le fichier `dovecot-uidlist` de chaque dossier donne l'UID d'un fichier Maildir.

**Paquet DSM vide.** Erreur 272 « Failed to acquire startup worker » ou
« Failed to run unit », journal `Acquire web-config … (fail)`. Compter les fichiers
vides dans `/volume1/@appstore/<paquet>` ; réinstaller le même `.spk` par
installation manuelle (circuit de mise à jour, données conservées).

## Enseignements et actions

1. **Étaler les tâches de nuit** : sauvegardes locales espacées de 10 minutes,
   DS212j après elles, une tâche Glacier par nuit. Calendrier dans
   [ADR-0014](../adr/0014-strategie-sauvegarde-3-2-1.md).
2. **Premiers envois** : ne lancer qu'un premier envoi long à la fois.
3. **Mises à jour des paquets** en notification seulement, appliquées hors des
   périodes de sauvegarde.
4. **Nettoyage des données** (data scrubbing) trimestriel ; le dernier datait du
   9 août 2023.
5. **Avant d'arrêter un NAS figé** : attendre la fin de l'arrêt normal ; l'arrêt
   forcé perd les écritures encore en mémoire. Ensuite, chercher les fichiers vides
   écrits pendant le blocage.
6. **Mémoire** : MailPlus (antivirus, antispam, Redis) occupe plus de 1,5 Go sur
   8 Go ; la [migration de la messagerie](../adr/0013-migration-messagerie-infomaniak.md)
   allège le NAS.
7. **Arrêt des bases pendant les sauvegardes** : toute tâche Hyper Backup qui
   inclut l'application MariaDB arrête MariaDB et WordPress (lisbonne2027.ch)
   environ 35 s par tâche, mesuré la nuit du 5 novembre (00:30, 03:10, 04:15).

## Suivi

Fait le 4 novembre 2026 : calendrier de nuit appliqué et vérifié dans
`/etc/crontab`, tâche Notes supprimée, sauvegarde MariaDB relancée avec succès,
3 messages de tonio et 2 messages de mimi rétablis.

Nuit du 4 au 5 novembre vérifiée le 5 novembre à 07:05 :

- aucun redémarrage ; `docker exec` répond pour `pihole` et `pihole2` ;
- toutes les sauvegardes réussies : Swiss Backup 00:30 (13 min), MailServerPlus
  03:00 (2 min), MariaDB 03:10 (78 s), WebStation 03:20 (19 s), Backups 03:30
  (30 s), DS212j 04:15 (11 min) ; Glacier PhotoBAK terminé avant 07:00 ;
- aucun fichier vide écrit depuis le 4 novembre 19:00 dans `web_packages`,
  `homes/tonio`, `Documents` et `docker` (hors `dhcp.leases` de `pihole2`, vide
  par nature) ; aucune erreur `Broken physical size` côté IMAP.

Dans `hyperbackup.log`, une tâche réussie s'écrit
`[err] … completes with result [1]` : le niveau `[err]` n'indique pas un échec.

Valeurs normales relevées (référence pour les seuils de surveillance) :

| Mesure | Normal (5 nov. 07:05) | Pendant l'incident |
|---|---|---|
| Charge (1 min) | ~3,5 | ~11 |
| Part attente disque de la charge | 0,5 à 1 | ~10 |
| Attente disque CPU (30 s) | ~9 % | — |
| Mémoire disponible | ~4,2 Go | — |
| Swap occupé | ~3 Go, stable (clamd ~0,9 Go) | 2,9 Go, actif |

Le swap occupé n'est pas un bon seuil : il reste haut au repos. Mesurer plutôt
l'activité (`pswpin`/`pswpout` de `/proc/vmstat`) et la charge d'attente disque
affichée par `uptime` (`[IO: …]`).

Reste à faire :

- surveillance de la saturation (voir ci-dessous) ;
- ~~supprimer `Development/Einstein.abime-20261104` (File Station) et l'instantané
  `web_packages` de sécurité du 4 novembre 18:13~~ : fait le 14 novembre 2026,
  après contrôle (aucun fichier propre au dossier, `.env` identiques au clone) ;
- ~~supprimer `~/Sauvegarde-Mails-20261104` et `~/Paquets-Synology-20261104` sur
  le Mac~~ : déjà fait, constaté le 14 novembre 2026.

### Prévention : surveillance de la saturation

Le blocage a duré environ 18 heures avant l'arrêt forcé, avec des signes
visibles dès le 3 novembre vers 14:40. Une alerte précoce aurait permis
d'interrompre les sauvegardes et de redémarrer proprement. À mettre en place :

- tâche DSM de contrôle toutes les 15 minutes, en échec (donc notifiée par
  courriel) si `docker exec` ne répond pas en 10 s, si l'attente disque reste
  élevée, si le swap dépasse un seuil ou si la mémoire disponible est trop basse ;
- procédure écrite en cas d'alerte : suspendre les tâches Hyper Backup et Glacier
  en cours, attendre la baisse de charge, redémarrer par DSM, jamais par
  l'interrupteur ;
- après tout arrêt non propre, recherche des fichiers vides écrits pendant les
  heures précédentes.

Notifications DSM relevées le 6 novembre 2026 : un seul profil, modèle
**All**, une seule adresse (`antonio.sanchez@chantevigne.com`, envoi par
Infomaniak). All envoie aussi des informations par courriel, par exemple
chaque sauvegarde réussie : la nuit du 7 novembre, `hyperbackup.log` indique
`[BackupTaskFinished] was sent to desktop,mail`, alors que
`/usr/syno/etc/notification/notification_filter.settings` ne prévoit pour
cette règle que le bureau, le mobile et CMS. Ce fichier ne dit donc pas quels
canaux DSM utilise réellement. Qu'une tâche planifiée terminée ou un
nettoyage des données fasse l'objet d'un courriel reste à vérifier. En
conséquence :

- la tâche de surveillance doit envoyer elle-même ses détails d'exécution
  (« uniquement si le script se termine anormalement »), à vérifier par un
  échec provoqué ;
- après chaque nettoyage des données, contrôler le résultat dans le
  Gestionnaire de stockage, ou faire vérifier l'état du RAID par la tâche de
  surveillance.
