# Incident du 1er novembre 2026 — suppression partielle de `/volume1`

- **Gravité :** majeure (perte de données système et utilisateur, services coupés)
- **Durée :** 20:19 → 23:25 (rétablissement des services), vérifications le lendemain
- **Cause :** commande de suppression fournie par l'assistant IA, exécutée en root
- **Perte définitive :** aucune donnée utilisateur connue ; fichiers de `Documents`
  créés ou modifiés entre 18:08 et 20:19 non récupérables, s'il y en avait

## Résumé

Pour supprimer des journaux du Planificateur de tâches DSM contenant un mot de
passe en clair, l'assistant a fourni une commande `find | xargs dirname | xargs rm -rf`.
Les chemins contenaient des espaces ; `xargs` les a découpés et l'un des morceaux
est devenu `/volume1`. La commande a exécuté `sudo rm -rf /volume1` pendant environ
quatre minutes avant de s'arrêter.

Les dossiers partagés touchés ont été restaurés depuis les instantanés Snapshot
Replication de 18:08. Les programmes des paquets ont été réinstallés sans perte de
configuration. La base PostgreSQL de DSM a été réinitialisée ; les contacts ont été
réimportés depuis la copie locale du Mac.

## Contexte

Le Planificateur de tâches DSM venait d'être configuré pour conserver la sortie des
tâches dans `/volume1/Rapports Synology/Planificateur de tâches`. Ce dossier était
lisible par tous les comptes. Une tâche y recopiait chaque minute sa ligne de
commande, qui contenait un identifiant et un mot de passe. Le mot de passe a été
sorti de la commande (fichier secret lu par `wget --post-file`), puis changé, et le
dossier a été réservé aux administrateurs. Il restait à supprimer les anciens
journaux.

## Cause

Commande fournie :

```bash
sudo find "/volume1/Rapports Synology/Planificateur de tâches/synoscheduler/25" \
    -name script.log -exec grep -l 'pass=' {} + | xargs -r -n1 dirname | xargs -r sudo rm -rf
```

`xargs` découpe son entrée sur les espaces. Le chemin
`/volume1/Rapports Synology/Planificateur de tâches/…/script.log` a produit les
arguments `/volume1/Rapports`, `Synology/Planificateur`, `de` et `tâches/…`, dont
`dirname` a tiré `/volume1`, `Synology`, `.` et `tâches/…`. Le second `xargs` a lancé
`rm -rf /volume1 …` en root.

Facteurs contributifs :

- suppression en root construite à partir d'un résultat calculé, sans chemin fixe ;
- aperçu proposé comme option, pas exigé avant exécution ;
- chemins avec espaces et accents pourtant connus dans la conversation.

## Dégâts constatés

| Élément | Effet | Restauration |
|---|---|---|
| `/volume1/@appstore` | supprimé : programmes des 43 paquets du volume | réinstallation manuelle des `.spk` |
| `/volume1/@database` | supprimé : données PostgreSQL de DSM | réinitialisation, bases vides |
| Dossier partagé `Backups` | supprimé (61 609 fichiers, 46 Go, destination Hyper Backup) | sous-volume recréé depuis l'instantané de 18:08 |
| `Documents` | 121 650 fichiers supprimés, dont `01_Famille`, `04_Clara`, `05_Noemie`, `03_Tonio/Travail` | copie depuis l'instantané de 18:08 |
| `@eaDir` | métadonnées et miniatures partiellement supprimées | régénérées par DSM |
| Autres dossiers partagés | intacts (comparaison avec les instantanés) | — |
| `@docker`, `/volume1/docker` | intacts | — |

Données perdues dans PostgreSQL : Synology Contacts (réimporté), Synology Calendar
(non utilisé), journal de transactions MailPlus, index du Serveur multimédia
(reconstruit), réglages du Service d'application. Note Station ne contenait pas de
notes.

## Chronologie

| Heure | Événement |
|---|---|
| 18:08 | Instantanés Snapshot Replication de tous les dossiers partagés |
| 20:19:44 | Exécution de la commande de suppression |
| ~20:24 | Fin de la suppression (dernière modification dans `Documents`) |
| 20:38 | `docker: command not found` ; découverte de l'absence de `@appstore` |
| 20:40–21:05 | Constat, inventaire `rsync --dry-run` contre les instantanés de 18:08 |
| ~21:30 | `Documents` restauré : 121 650 fichiers, contrôle à 0 manquant |
| ~21:33 | `Backups` recréé par `btrfs subvolume snapshot` depuis l'instantané |
| 21:37–21:39 | Sauvegarde de la base Contacts du Mac et export vCard (1 488 fiches) |
| 21:45 | `@appstore` recréé vide ; les paquets passent de « anomalie de stockage » à réinstallables |
| 21:49–22:41 | Réinstallation des paquets ; dépendances contournées par installation manuelle |
| 22:05–22:13 | Script d'arrêt de MailPlus Server bloqué, interrompu ; messagerie arrêtée |
| 22:43–22:47 | PostgreSQL arrêté, `@database/pgsql` recréé, base réinitialisée par DSM |
| 22:48–22:51 | Service d'application, Serveur multimédia, AI Console, Drive Server |
| 22:53 | Mise à jour de Container Manager ; conteneurs tués en boucle (code 137) |
| 22:54–23:06 | **DNS du LAN coupé** (les deux Pi-hole sur le même Docker) |
| 23:06 | Container Manager arrêté, six `containerd-shim` orphelins arrêtés, redémarrage : DNS rétabli |
| 23:12–23:18 | MailPlus Server, Contacts, Calendar, Note Station, MailPlus réparés |
| ~23:15 | Messagerie rétablie (SMTP 25/465/587, IMAPS 993) |
| ~23:25 | 1 488 contacts réimportés dans Synology Contacts |

## Restauration : points techniques

**Dossiers partagés.** Copie sans écrasement ni suppression, après aperçu en root :

```bash
sudo rsync -a --dry-run --ignore-existing --stats "<instantané>/" "/volume1/<dossier>/"
```

puis la même commande sans `--dry-run`. Un dossier partagé entièrement supprimé
mais toujours déclaré dans DSM se recrée instantanément :

```bash
sudo btrfs subvolume snapshot "/volume1/@sharesnap/<dossier>/<instantané>" "/volume1/<dossier>"
```

**Paquets.** Sans `@appstore`, le Centre de paquets affiche « anomalies de stockage »
et grise « Réparer ». Recréer `/volume1/@appstore` vide (`root:root`, 0755) rend les
paquets réinstallables. La désinstallation (« Uninstall only ») désinstalle aussi les
paquets dépendants ; l'**installation manuelle du même `.spk`** (archive Synology,
même version et architecture `x86_64`) passe par le circuit de mise à jour, conserve
`@appconf`, `@appdata`, `@apphome` et ne touche pas aux dépendants.

**Scripts d'arrêt bloqués.** Un script d'arrêt qui appelle des programmes absents
peut boucler (délai systemd d'une heure pour MailPlus Server). L'arrêter par son PID,
après vérification, laisse systemd arrêter proprement les sous-services.

**PostgreSQL.** Le script `/usr/lib/systemd/scripts/pgsql.sh` initialise une base
vide si `base/` manque, mais refuse de démarrer si `servicetool --get-service-path
pgsql` ne trouve pas `/volume1/@database/pgsql`. Recréer `/volume1/@database`
(`root`, 0755) et `pgsql` (`postgres`, 0700), puis redémarrer `pgsql-adapter` et
`pgsql`.

**Docker.** Après la mise à jour de Container Manager, des `containerd-shim`
orphelins de l'ancien démon faisaient croire à `containerd` que les tâches tournaient
encore ; chaque conteneur était tué au démarrage (code 137, sans `OOMKilled` ni
événement `kill`). Arrêter Container Manager, vérifier que les shims n'ont plus de
processus enfant, les arrêter, puis relancer Container Manager.

**Contacts.** Un client CardDAV garde une copie locale complète. Avant toute
réparation : copie de `~/Library/Application Support/AddressBook` et export vCard
depuis Contacts sur le Mac, sans désactiver le compte (ce qui supprimerait la copie
locale).

## État final et vérifications

- 43 paquets du volume avec leurs programmes ; C2 Identity désinstallé (non utilisé).
- Pi-hole, Einstein, Homebridge, nebula-sync en service ; DNS filtrant sur `.56` et `.57`.
- Hyper Backup, Snapshot Replication, Synology Drive et messagerie contrôlés le
  lendemain par le propriétaire.
- Contacts : 1 488 sur le serveur et sur le Mac. **iPhone à vérifier** : il n'affichait
  que 8 contacts en fin de soirée (synchronisation en cours ou autre carnet).

## Enseignements et actions

1. **Commandes destructives.** Ne jamais construire un `rm` avec `xargs`, `$(…)` ou
   une liste calculée ; cibler un chemin fixe ; fournir d'abord une commande
   d'aperçu et la faire valider. Préférer l'interface DSM (File Station) pour les
   suppressions ponctuelles. Règle enregistrée dans la mémoire de l'assistant ;
   à ajouter aussi à `AGENTS.md`.
2. **Instantanés.** Ils ont permis de restaurer toutes les données utilisateur.
   `@appstore` et `@database` ne sont pas des dossiers partagés et ne sont pas
   couverts.
3. **Sauvegarde Contacts.** La tâche Hyper Backup `CardDAV` datait de 2021. Ajouter
   Synology Contacts à une tâche Hyper Backup régulière.
4. **Sauvegardes hors du NAS.** La destination Hyper Backup (`Backups`) est sur le
   même volume ; elle n'a survécu que grâce à son instantané. Prévoir une copie
   externe.
5. **Redondance DNS.** Les deux Pi-hole partagent le même Docker : la panne de
   Docker a coupé le DNS du LAN 12 minutes (limite déjà connue, voir
   [ADR-0012](../adr/0012-pihole-secondaire.md)).
6. **Journaux du Planificateur.** Ils recopient la commande des tâches : dossier
   réservé aux administrateurs, aucun secret dans une commande.
