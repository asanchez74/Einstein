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
| Wi-Fi Synology | RT2600ac — `192.168.1.2`, mode point d'accès, + 2 MR2200ac (mesh) |
| LAN | 192.168.1.0/24 |
| NAS | 192.168.1.3 |
| DS212j (KNX `eibd`/`linknx`, copie de sauvegarde) | 192.168.1.4, adresse fixe depuis le 10 novembre 2026 |
| Domaine | nas.chantevigne.com |

### Topologie

```text
Internet (fibre)
  └─ FRITZ!Box 5530 192.168.1.1   routeur, passerelle, NAT, redirections
       └─ switch Netgear (1 Gbit/s)
            ├─ NAS DS918+ 192.168.1.3   DHCP du LAN, DNS (Pi-hole .56/.57), OpenVPN
            ├─ RT2600ac 192.168.1.2 (port WAN)   point d'accès Wi-Fi, rez-de-chaussée
            │    ├─ MR2200ac, étage          (mesh Wi-Fi)
            │    └─ MR2200ac, sous-sol       (mesh Wi-Fi)
            └─ autres appareils filaires
```

Le Synology RT2600ac (SRM 1.2.5-8227 Update 11) fonctionne en **point
d'accès sans fil** : il ne route pas, ne fait ni DHCP ni DNS, et place les
clients Wi-Fi dans le LAN `192.168.1.0/24` (passerelle FRITZ!Box). Il est
relié au switch par son port WAN, en 1 Gbit/s, et pilote deux satellites
MR2200ac en mesh (étage et sous-sol). Constaté le 14 novembre 2026 : premier
saut vers Internet `192.168.1.1`, port 53 fermé sur `.2`, interface SRM sur
8000/8001, exposée en `https://router.chantevigne.com` par le proxy inverse
du NAS. Les noms `router` et `router.chantevigne.com` le désignent (adresse
confirmée le 16 octobre 2026).

Le NAS et le RT2600ac partagent le même switch : une panne du switch coupe à
la fois le Wi-Fi, le DNS et le DHCP du LAN.

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
