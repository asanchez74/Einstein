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
