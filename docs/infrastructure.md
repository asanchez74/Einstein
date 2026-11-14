# Infrastructure actuelle

!!! info "État"

    Ce document décrit l'infrastructure de référence d'Einstein.

## NAS

| Élément | Valeur |
|----------|---------|
| Modèle | Synology DS918+ |
| DSM | 7.2.2 Update 9 |
| RAM | 8 Go |
| Stockage | SHR 10.9 To |
| Libre | 3.9 To |
| Cache SSD | 2 × 465 Go |

## Réseau

| Élément | Valeur |
|----------|---------|
| FRITZ!Box | 5530 Fiber — `192.168.1.1` |
| Routeur Synology | RT2600ac — `192.168.1.2` |
| LAN | 192.168.1.0/24 |
| NAS | 192.168.1.3 |
| DS212j (KNX `eibd`/`linknx`, copie de sauvegarde) | 192.168.1.4, adresse fixe depuis le 10 novembre 2026 |
| Domaine | nas.chantevigne.com |

Les noms DNS `router` et `router.chantevigne.com` désignent le Synology
RT2600ac, distinct du NAS. Son adresse a été confirmée par le propriétaire
le 16 octobre 2026. La capture de son panneau de configuration indique
SRM 1.2.5-8227 Update 11. Son rôle précis dans la topologie réseau reste à
documenter.

## Services

- Synology Drive (accès extérieur par OpenVPN seulement, port 6690 fermé le
  6 novembre 2026)
- Homebridge (Hue, Google Smart Home, KNX via `eibd` du DS212j), stack
  `compose/homebridge/` ([ADR-0015](adr/0015-homebridge-compose.md))
- Container Manager
- Reverse Proxy
- OpenVPN
- WordPress `lisbonne2027.ch` (paquet DSM, Web Station, voir ci-dessous)

## WordPress lisbonne2027.ch

| Élément | Valeur |
|---|---|
| Code | `/volume1/web_packages/wordpress`, propriétaire `WordPress:http` |
| PHP | profil Web Station PHP 8.2, pool PHP-FPM exécuté en `WordPress` |
| WP-Cron | tâche DSM « WP-Cron lisbonne2027.ch », root, toutes les 5 minutes |
| Sauvegarde | UpdraftPlus : base chaque jour à 07:14, fichiers le lundi, envoi FTP vers le DS212j (`SauvegardeDS918/lisbonne2027`) |
| DNS | zone chez **QUIC.cloud** (`jon.quicns.com`, `kevin.quicns.com`, extension LiteSpeed Cache, CDN activé), domaine enregistré chez Infomaniak |
| Messagerie | Infomaniak (MX `mta-gw.infomaniak.ch`, SPF Infomaniak, DMARC `p=reject`, DKIM `20260219`) |

La zone DNS active est celle de QUIC.cloud (my.quic.cloud), importée le
6 mars 2026 : la zone visible dans le Manager Infomaniak n'est pas publiée
et ses modifications restent sans effet. La clé DKIM Infomaniak
`20260219._domainkey`, absente de l'import, a été ajoutée chez QUIC.cloud le
14 novembre 2026 (les mails du site échouaient en `dkim=fail`, acceptés
seulement grâce au SPF).

La tâche WP-Cron exécute :

```sh
su -s /bin/sh WordPress -c "/usr/local/bin/php82 /volume1/web_packages/wordpress/wp-cron.php"
```

Elle doit tourner sous `WordPress`, l'utilisateur du pool PHP-FPM. Créée le
1er novembre 2026 sous `http`, qui ne peut pas écrire dans
`wp-content/updraft` (`755`) : les sauvegardes planifiées échouaient
(« Impossible de créer des fichiers dans le répertoire de sauvegarde »), sans
journal, tandis que les sauvegardes manuelles, exécutées par PHP-FPM,
réussissaient. Corrigé le 12 novembre 2026 ; sauvegarde planifiée réussie et
envoyée au DS212j le 14 novembre.

`DISABLE_WP_CRON` n'est pas défini, contrairement à ce qu'indique le
commentaire du script : le cron déclenché par les visites reste actif, sous
le même utilisateur.

La messagerie est chez Infomaniak, les contacts et agendas dans iCloud depuis
le 6 novembre 2026 ([ADR-0013](adr/0013-migration-messagerie-infomaniak.md)) ;
MailPlus Server est arrêté en attendant sa désinstallation.

## Numérisation

L'imprimante HP enregistre ses scans par SMB, profil « NAS » de la fonction
« Numérisation vers le dossier réseau » :

| Élément | Valeur |
|---|---|
| Chemin | `\\192.168.1.3\Documents\00_A_traiter\Scans_entrant` |
| Compte DSM | `scan`, membre de `users` seulement |
| Droits | lecture et écriture sur le partage `Documents` |
| Nom des fichiers | `AAAAMMJJ_scan.pdf` (PDF couleur, 600 ppp) |

Avant le 7 novembre 2026, les scans allaient dans le partage `Scan`. DSM gère
les droits de `Documents` au niveau du partage : `scan` peut donc écrire dans
tout `Documents`, ce qu'atténuent les instantanés quotidiens et Swiss Backup.
Un « Pas d'accès » donné à un groupe l'emporte sur les droits de
l'utilisateur : `scan` a été retiré du groupe de comptes de services qui
n'avait pas accès à `Documents`. Quand une imprimante HP affiche
« Informations d'identification incorrectes », vérifier aussi les droits sur
le partage, pas seulement le mot de passe.

!!! success "Objectif"

    Toute cette infrastructure sera progressivement documentée automatiquement par Einstein.
