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
| Domaine | nas.chantevigne.com |

Les noms DNS `router` et `router.chantevigne.com` désignent le Synology
RT2600ac, distinct du NAS. Son adresse a été confirmée par le propriétaire
le 16 octobre 2026. La capture de son panneau de configuration indique
SRM 1.2.5-8227 Update 11. Son rôle précis dans la topologie réseau reste à
documenter.

## Services

- Synology Drive
- Synology Mail Server
- Homebridge
- Container Manager
- Reverse Proxy
- OpenVPN

!!! success "Objectif"

    Toute cette infrastructure sera progressivement documentée automatiquement par Einstein.
