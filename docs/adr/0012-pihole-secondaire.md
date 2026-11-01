# ADR-0012 — Pi-hole secondaire synchronisé par nebula-sync

- **Statut :** déployé, validé et distribué par le DHCP le 1er novembre 2026
- **Date :** 1er novembre 2026

## Contexte

Le Pi-hole principal `192.168.1.56` tourne sur le DS918+ en macvlan
(`ovs_bond0`) avec un bridge `172.23.0.0/24`. Le second DNS distribué par
le DHCP est la FRITZ!Box, qui ignore les noms locaux et ne filtre pas
(voir [Pi-hole](../pihole-operations.md)). Le port 53 du NAS est occupé
par le paquet DNS Server de DSM.

## Décision

- Ajouter un Pi-hole secondaire `192.168.1.57`, stack `compose/pihole2/`,
  données `/volume1/docker/einstein/data/pihole2`.
- Le service étend celui du principal (`extends`) : image et
  configuration DNS sont identiques par construction.
- Le secondaire rejoint les réseaux de la stack `pihole` : Docker refuse un
  second réseau macvlan sur la même interface parente.
- `nebula-sync` tourne sur le NAS, sur le bridge partagé. Le principal est
  lui-même sur le NAS : aucun autre hôte n'est disponible, et la limite
  hôte↔macvlan ne concerne pas les échanges entre conteneurs d'un bridge.
  Synchronisation complète (Teleporter) et gravity toutes les heures.
- Secrets nebula-sync dans `/volume1/docker/einstein/secrets/`, hors dépôt.

## Conséquences

- Couvre l'arrêt, la mise à jour ou la corruption d'un conteneur, et permet
  de mettre à jour les instances l'une après l'autre. Ne couvre **pas** la
  perte du NAS ou de Docker : les deux instances partagent l'hôte.
- La stack `pihole2` dépend des réseaux de `pihole`.
- Toute modification se fait sur le principal ; le secondaire est écrasé
  chaque heure.
- `synology-hosts.list` n'est pas synchronisé par Teleporter ; le script DHCP
  écrit dans les deux volumes (`PIHOLE_TARGETS`).
- Le DHCP distribue `.56` puis `.57` ; la FRITZ!Box n'est plus un repli
  pour les clients. Arrêter les deux instances coupe la résolution du LAN.

## Réévaluation

Placer le secondaire sur un autre matériel si la perte du NAS doit être
couverte.
