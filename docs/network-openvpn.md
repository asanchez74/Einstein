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

## Routage retour vers les clients VPN

Le 17 octobre 2026, une route retour incorrecte a été diagnostiquée pour
l'accès VPN à l'adresse LAN du NAS. L'exception temporaire de priorité 1
est validée : readiness et questions IA fonctionnent via le nom DNS normal,
sans `--resolve`. Voir l'[ADR-0008](adr/0008-routage-retour-openvpn.md).

Après commit, push et `git pull --ff-only` sur le NAS, vérifier le script :

```bash
cd ~/Development/Einstein
./scripts/vpn-return-route.sh --check
sudo ./scripts/vpn-return-route.sh --apply
ip -4 route get 10.8.0.6 from 192.168.1.3
```

Adapter l'adresse client au bail VPN actuel ; la route attendue utilise
`tun0`. Si la règle temporaire est déjà présente, `--apply` ne la duplique pas.
La priorité 1 doit être réservée à cette exception ; un conflit est une erreur
à analyser, pas une autorisation d'écraser une règle.

### Planification DSM à installer

Créer une tâche exécutée par root au démarrage, puis une tâche récurrente
toutes les cinq minutes, avec la même commande :

```bash
/bin/sh /var/services/homes/tonio/Development/Einstein/scripts/vpn-return-route.sh --apply
```

Le script ne fait aucune modification si le tunnel n'est pas prêt et réessaie
lors de la prochaine exécution. S'assurer que le clone de déploiement est
accessible à la tâche. Éviter les exécutions concurrentes de ces tâches.
Le mode `--check` retourne 0 si la règle exacte est présente, 1 sinon.

Le 17 octobre 2026, le propriétaire confirme la readiness via le nom DNS
normal après reconnexion VPN et la présence de l'exception via `--check`.
L'installation des tâches reste à confirmer explicitement. Le contrôle après
redémarrage DSM est reporté à un autre créneau, avec accès de récupération
disponible ; il n'a pas été réalisé.

### Retour arrière

Désactiver les deux tâches DSM, puis retirer uniquement l'exception :

```bash
sudo ./scripts/vpn-return-route.sh --remove
```

Le script refuse de supprimer une règle différente à la priorité 1. Le retrait
réintroduit le problème de retour VPN observé tant que le routage DSM reste
identique. Il ne modifie ni DNS ni pare-feu.
