# Incident du 4 novembre 2026 — saturation du NAS et perte d'écritures

- **Gravité :** majeure (données récentes perdues, messagerie et Drive indisponibles)
- **Durée :** 3 novembre ~14:40 (premiers symptômes) → 4 novembre 18:15 (dernières réparations)
- **Cause :** NAS saturé (disque et mémoire) pendant les premiers envois de sauvegarde,
  puis arrêt par l'interrupteur alors que les écritures n'étaient pas sur disque
- **Perte définitive :** aucune donnée utile connue ; deux mails de Mimi (06:16 et
  07:08) à faire renvoyer s'ils ne sont sur aucun appareil

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
| Messagerie mimi | 4 mails vides (2 réception reçus à 06:16 et 07:08, 2 corbeille) | `doveadm expunge` par UID ; messages à faire renvoyer s'ils ne sont sur aucun appareil |
| WordPress (`web_packages`) | 16 113 fichiers vides | restauration de l'instantané du 4 novembre 00:00:05 |
| Dépôt Einstein du NAS | objets git et 4 fichiers du `git pull` vides ; script DHCP vide | nouveau clone, `.env` recopiés, ancien dossier renommé `Einstein.abime-20261104` |
| Sauvegarde Homebridge 04:00 | vide | refaite la nuit suivante |
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
   environ 2 min 30 (00:30, 03:10, 04:15).

## Suivi

Fait le 4 novembre 2026 : calendrier de nuit appliqué et vérifié dans
`/etc/crontab`, tâche Notes supprimée, sauvegarde MariaDB relancée avec succès.

Reste à faire :

- remettre les 3 messages de tonio depuis la boîte locale du Mac ;
- faire renvoyer les 2 messages de mimi si nécessaire ;
- vérifier la nuit du 4 au 5 novembre (sauvegardes, `docker exec`, fichiers vides) ;
- supprimer `Development/Einstein.abime-20261104` (File Station) et l'instantané
  `web_packages` de sécurité du 4 novembre 18:13 ;
- supprimer `~/Sauvegarde-Mails-20261104` et `~/Paquets-Synology-20261104` sur le
  Mac une fois les messages remis.
