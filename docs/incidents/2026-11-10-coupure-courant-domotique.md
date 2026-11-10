# Incident du 10 novembre 2026 — coupure de courant et domotique

- **Gravité :** mineure (HomeKit partiellement indisponible, aucune donnée perdue)
- **Durée :** 10 novembre ~18:01 (retour du courant) → 18:43 (`eibd` relancé)
- **Cause :** au redémarrage simultané des deux NAS, Homebridge bloqué par le
  délai de s6 sur le DS918+, et `eibd` lancé sans réseau sur le DS212j
- **Perte :** aucune
- **Statut :** volet `eibd` (DS212j) clos le 10 novembre 2026 ; volet Homebridge
  suivi par l'[ADR-0015](../adr/0015-homebridge-compose.md)

## Résumé

Après une coupure de courant, le DS918+ et le DS212j ont redémarré ensemble.
Deux défauts indépendants sont apparus ; le diagnostic a aussi mis au jour une
panne plus ancienne de KNX dans HomeKit.

**Homebridge (DS918+).** Le conteneur DSM `Homebridge` (`oznu/homebridge`)
installe les plugins par npm au démarrage. s6-overlay accorde 5 s aux services
d'initialisation ; NAS chargé, npm a duré 14 s, s6 a abandonné
(`s6-rc: fatal: timed out`) et Homebridge n'a pas démarré, conteneur « Up » et
sans healthcheck. Un redémarrage manuel à 18:11 a réussi. Même cause probable
pour les plantages « parfois au démarrage » constatés auparavant. Correction :
stack Compose `homebridge/homebridge` avec
`S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0` ([ADR-0015](../adr/0015-homebridge-compose.md)).

**`eibd` (DS212j).** Le serveur DHCP du LAN est sur le DS918+, lui-même en
cours de démarrage. Le DS212j a pris une adresse de secours
`169.254.37.121`, a lancé `eibd` et `linknx` par `rc.local` (Optware,
`/opt/etc/init.d/S98eibd`), puis a reçu `192.168.1.4` sept minutes plus tard.
`eibd` ne tournait plus ; `linknx` si. La clé KNX-USB Berker était détectée
dès 40 s : l'USB n'est pas en cause.

**KNX hors de HomeKit depuis le 10 juin 2026.** Sans lien avec la coupure :
`homebridge-knx` 0.5.0-beta.12 ne s'initialise plus depuis le passage à
Homebridge 2.1.0 (voir l'ADR).

## Chronologie

| Heure | Événement |
|---|---|
| ~18:01 | Retour du courant, démarrage des deux NAS |
| 18:03:50 | DS212j : pas de bail DHCP, `eth0` → `169.254.37.121` |
| ~18:04 | DS212j : `rc.local` lance `eibd` et `linknx` (PID d'origine 5316) |
| 18:05:43 | DS918+ : Homebridge, `s6-rc: fatal: timed out` |
| 18:10:30 | DS212j : bail DHCP `192.168.1.4` ; `eibd` absent ensuite |
| 18:10:59 | DS918+ : conteneur Homebridge redémarré, démarrage normal |
| 18:43 | DS212j : `sudo /opt/etc/init.d/S98eibd restart`, port 6720 de nouveau ouvert |

`eibd` ne journalise rien dans syslog : sa fin exacte (au changement
d'adresse ou dès le lancement) n'est pas observable. Indice concordant : aux
arrêts du DS212j de janvier et février 2026, DSM ne tue que `linknx` parmi les
processus d'`/opt`.

## Corrections

| Où | Correction | État |
|---|---|---|
| DS212j | Adresse fixe `192.168.1.4/24`, passerelle `192.168.1.1`, DNS `.56` puis `.57` (réservation DHCP conservée) | fait le 10 novembre |
| DS212j | Tâche DSM « Eibd restart », root, toutes les 5 min : `pidof eibd >/dev/null \|\| { /usr/bin/logger -t eibd "eibd absent, redémarrage"; /opt/etc/init.d/S98eibd restart; }` | fait le 10 novembre |
| DS918+ | Stack `compose/homebridge/` ([ADR-0015](../adr/0015-homebridge-compose.md)) | à déployer |
| DS918+ | Homebridge 2.5.0 et `homebridge-knx` 0.6.0 | après la migration |

Un redémarrage relancé par la tâche laisse une ligne `eibd` dans
`/var/log/messages` du DS212j.

## Enseignements

- Le DS212j dépendait du DS918+ (DHCP) pour démarrer correctement : une
  coupure générale est le cas où les deux redémarrent ensemble.
- Un conteneur « Up » n'est pas un service qui marche : healthcheck à prévoir
  pour chaque conteneur, y compris ceux créés hors du dépôt.
- L'envoi de mail du DS212j échoue (`mail.chantevigne.com` non résolu depuis
  la migration vers Infomaniak) : ses notifications ne partent pas.
