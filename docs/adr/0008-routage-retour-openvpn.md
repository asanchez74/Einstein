# ADR-0008 — Routage retour du NAS vers OpenVPN

- **Statut :** correction temporaire validée ; persistance préparée, non installée
- **Date :** 17 octobre 2026

## Diagnostic observé

Sur mobile + VPN, le DNS résout Einstein vers `192.168.1.3` et la route du
Mac emprunte le tunnel. Les SYN arrivent sur `tun0`, sans réponse sur cette
interface. La requête fonctionne en ciblant `10.8.0.1` avec le même nom TLS.

DSM applique `from 192.168.1.3 lookup ovs_bond0-table` à la priorité 3.
Cette table ne contient pas la route VPN et renvoie vers `192.168.1.1`.
La table `main` contient `10.8.0.0/24 via 10.8.0.2 dev tun0`.

## Décision

Ajouter une exception de priorité 1, après `local` (0) et avant les règles
DSM (2 et 3), strictement limitée à :

```text
from 192.168.1.3/32 to 10.8.0.0/24 lookup main
```

L'ajout manuel a rétabli readiness et question IA via le DNS normal sur VPN.
Aucune modification du DNS, du pare-feu ou de la route par défaut n'est requise.

## Persistance proposée

Le script versionné `scripts/vpn-return-route.sh` contrôle, applique ou retire
uniquement cette exception. Il refuse une priorité 1 occupée par une autre
règle ou par des doublons. L'application est différée si la route VPN via
`tun0` n'est pas présente. Aucun fichier réseau interne DSM n'est modifié.

Configurer des tâches DSM root au démarrage et toutes les cinq minutes
pour réappliquer l'exception après une remise à zéro des règles réseau.
Cela implique un délai maximal lié à la planification si DSM retire la règle.
La tâche et sa tenue au redémarrage/reconnexion restent à valider sur le NAS.

## Retour arrière et réévaluation

Désactiver les tâches avant `--remove`, sinon elles recréeraient la règle.
Réévaluer si adresse NAS, réseau VPN, interface tunnel, tables ou priorités
changent. Ne pas supprimer les règles DSM ni toucher aux règles Docker.

## Référence

[Manuel iproute2 : ip rule](https://man7.org/linux/man-pages/man8/ip-rule.8.html)
