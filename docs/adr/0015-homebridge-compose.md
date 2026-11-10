# ADR-0015 — Homebridge géré par Docker Compose

- **Statut :** accepté, migration à faire
- **Date :** 10 novembre 2026

## Contexte

Homebridge tourne dans un conteneur `Homebridge` créé dans DSM le
6 juillet 2023 à partir de `oznu/homebridge:latest` (image de janvier 2023,
abandonnée au profit de `homebridge/homebridge`). Node 24 et l'interface v5
n'existent que dans la couche modifiable du conteneur : recréer le conteneur
avec cette image (fonction « Dupliquer » de DSM, seule façon d'y changer une
variable d'environnement) ramènerait l'ancien Node, refusé par Homebridge 2.

Constats du 10 novembre 2026 :

- **Démarrage bloqué.** Au démarrage, l'image installe les plugins par npm.
  s6-overlay accorde 5 s aux services d'initialisation ; NAS chargé juste
  après le boot, npm a duré 14 s, s6 a affiché `s6-rc: fatal: timed out` et
  Homebridge n'a pas démarré. Le conteneur restait « Up », sans
  healthcheck : la politique `always` ne pouvait rien. Un redémarrage manuel
  5 minutes plus tard a réussi (npm : 1 s).
- **KNX hors service depuis le 10 juin 2026.** Passage à Homebridge 2.1.0 ;
  `homebridge-knx` 0.5.0-beta.12 échoue à l'initialisation (`Class
  constructor Characteristic cannot be invoked without 'new'`). Les
  7 accessoires KNX (4 variateurs, 3 sondes) ont disparu de HomeKit.
  `homebridge-knx` 0.6.0 (27 octobre 2026) corrige la compatibilité.
- **Versions.** `homebridge-hue` 0.15.10 demande Homebridge ≥ 2.4.0 et
  Node 22 ou 24.
- **`eibd`.** Le port TCP 6720 du DS212j refusait les connexions : `eibd`
  n'avait pas survécu au boot sans réseau qui a suivi la coupure de courant.
  Relancé, adresse fixe et surveillance ajoutées
  ([incident du 10 novembre 2026](../incidents/2026-11-10-coupure-courant-domotique.md)).
- Ni limite mémoire réelle (8 Go), ni rotation des logs Docker, avahi du
  conteneur en concurrence avec celui de DSM.

## Décision

- Stack `compose/homebridge/`, image `homebridge/homebridge`, ligne
  `synology` (Ubuntu 22.04, prévue pour les noyaux DSM anciens), tag daté
  `synology-2026-11-02` (Node 24.22). Le tag `synology-2026-11-10` passe à
  Node 26, non déclaré par `homebridge-hue`.
- Données conservées à `/volume1/docker/Homebridge`, montées sur
  `/homebridge` comme avant : configuration, plugins et identité HomeKit
  inchangés, pas de nouvel appairage.
- `S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0`, `ENABLE_AVAHI=0` (annonce par ciao).
- Réseau `host` (exigé par HomeKit), `mem_limit: 1536m` (environ 640 Mo
  mesurés sans KNX), `cpu_shares: 1024`, `no-new-privileges`, healthcheck sur
  l'interface, logs `local` avec rotation.
- Ancien conteneur arrêté, sans redémarrage automatique, conservé quelques
  jours pour le retour arrière.
- Mise à jour de Homebridge (2.5.0) et de `homebridge-knx` (0.6.0) dans un
  second temps, depuis l'interface, une fois la migration validée.

## Conséquences

- Déploiement par `scripts/stack-up.sh`, sauvegarde par `backup-stack.sh`.
- Exceptions aux conventions Docker : pas de `read_only` ni de
  `cap_drop: ALL` (s6-overlay en root, npm écrit au démarrage) ; réseau de
  l'hôte, donc interface exposée sur le LAN comme auparavant.
- Les plugins restent gérés dans `package.json` du volume par l'interface ;
  l'image ne fixe que Node, l'interface et le superviseur.
- Le healthcheck ne couvre que l'interface ; Docker ne redémarre pas un
  conteneur `unhealthy`.
- KNX dépend toujours d'`eibd` sur le DS212j (DSM 6.2.4 sans mises à jour).

## Réévaluation

Remplacer `eibd` sur le DS212j (par `knxd`, ou une interface KNX/IP) si le
DS212j est retiré ou si `eibd` reste instable.
