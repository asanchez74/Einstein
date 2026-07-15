# OpenVPN

!!! success "Statut"

    Configuration validée le 15 juillet 2026.

## Objectif

Permettre un accès sécurisé au NAS depuis Internet sans exposer les services internes.

## Infrastructure

| Élément | Valeur |
|----------|---------|
| Routeur | FRITZ!Box 5530 Fiber |
| Serveur | Synology DS918+ |
| VPN | OpenVPN |
| Port | UDP 1194 |
| Adresse VPN du NAS | 10.8.0.1 |

## Authentification

- Utilisateur DSM
- Clé TLS intégrée
- Chiffrement AES-256-CBC
- SHA256

## SSH

Administration via :

```bash
ssh einstein
```

Configuration SSH :

- Host : einstein
- Adresse : 10.8.0.1
- Port : 22606

## Validation

Tests réalisés :

- ✅ Tunnel VPN
- ✅ Attribution d'une adresse 10.8.0.x
- ✅ SSH via VPN
- ✅ VS Code Remote SSH