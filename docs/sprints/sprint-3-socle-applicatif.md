# Sprint 3 — Socle applicatif Einstein

## Statut

**Terminé — clôture documentaire le 16 octobre 2026.**

Déploiement fonctionnel validé au commit
`0c99e5d43b1c183cbd8325a87f2c35c929942f09` sur le Synology DS918+.
Cette clôture porte sur le socle applicatif ; aucune fonction métier ni
intégration de modèle IA n'est encore livrée.

## Objectif et architecture

Construire une API légère, modulaire, testée et déployable sur le NAS :
Python 3.14, FastAPI, Uvicorn, Pydantic Settings, pytest et Docker Compose.
Le monolithe modulaire sans base de données est défini par l'ADR-0005.

## Livrables

- [x] architecture applicative et ADR-0005 ;
- [x] structure Python sous `src/` ;
- [x] configuration par variables d'environnement `EINSTEIN_` ;
- [x] journalisation applicative JSON ;
- [x] endpoints `/health/live`, `/health/ready` et `/version` ;
- [x] 8 tests automatisés validés localement ;
- [x] Dockerfile et stack Compose ;
- [x] image construite sur le NAS (validation historique consignée) ;
- [x] déploiement final et healthcheck Docker ;
- [x] accès local et reverse proxy Synology ;
- [x] documentation opérationnelle ;
- [x] périmètre des secrets documenté, implémentation différée au premier besoin ;
- [x] preuves de validation NAS consolidées avec commit de déploiement.

## Configuration et exploitation

Voir le [guide Einstein Core](../einstein-core-operations.md) pour les
variables, le déploiement, les contrôles HTTP, les logs et le redémarrage.

Le conteneur utilise l'UID/GID `10001:10001`, une racine en lecture seule,
`no-new-privileges`, `cap_drop: ALL`, une limite mémoire de 256 Mio et
`cpu_shares: 256`. Le port est publié sur `127.0.0.1:18081`.

La politique choisie par le propriétaire autorise le LAN `192.168.1.0/24`
et OpenVPN `10.8.0.0/24`, sans accès applicatif depuis Internet. Cette politique
remplace la description initiale « VPN uniquement ». Elle repose sur DSM et
le réseau ; le Core n'implémente pas d'authentification.

Aucun secret ni volume persistant n'est requis par le Core actuel.
Le guide décrit le futur stockage hors Git et la lecture explicite de fichiers
secrets à implémenter avec le premier besoin. Aucune prise en charge `*_FILE`
n'est déclarée existante. `backup-stack.sh` ne s'applique pas au Core sans état.

## Vérifications locales

Le 16 octobre 2026, sous Python 3.14.4 :

- 8 tests réussis : endpoints nominaux, configuration par défaut et par
  environnement, rejet de valeurs invalides, démarrage et arrêt ;
- `compileall` réussi ;
- build MkDocs strict réussi ;
- `git diff --check` réussi.

La readiness est statique, le service n'ayant aucune dépendance externe.
Les logs applicatifs sont en JSON ; les loggers Uvicorn ne sont pas
explicitement configurés avec ce formateur.

## Incident et réconciliation NAS

Le contrôle initial a constaté le clone NAS au commit `1d98275`, le Core
inaccessible en local et HTTP 502 via HTTPS. Les sorties terminal du
propriétaire ont confirmé un conteneur arrêté (`Exited (143)`) et un arrêt
propre dans les logs le 14 octobre à 09:02:40 UTC. La cause reste inconnue.

Le conteneur existant a été relancé, puis inspecté : `healthy`, politique
`unless-stopped`, `OOMKilled=false`. Ces valeurs ne déterminent pas la cause
de l'arrêt antérieur.

Les modifications Pi-hole du NAS ont été préservées dans un stash nommé
`Pi-hole NAS avant reconciliation Sprint 3`, sans réapplication. Le fichier
`compose.yaml.bak-20261014` est intact. Le clone a été mis à jour par
`git pull --ff-only` vers `0c99e5d`, puis le propriétaire a exécuté
`stack-up.sh einstein-core` et `stack-up.sh pihole` avec succès.

Le réglage Pi-hole `cpu_shares: 2048` a été conservé sur décision du
propriétaire. Les noms `router` et `router.chantevigne.com` désignent le
Synology RT2600ac à `192.168.1.2`.

## Matrice de validation

Les sorties ci-dessous ont été transmises par le propriétaire lors de la
séquence de validation. Les premiers contrôles précèdent le redéploiement ;
ils sont distingués des contrôles finaux.

| Contrôle | Résultat | Moment |
|---|---|---|
| Core et Pi-hole démarrés par les scripts | Succès | Après mise à jour vers `0c99e5d` |
| Healthcheck Core | `healthy` | Après redéploiement |
| Healthcheck Pi-hole | `healthy` | Après redéploiement |
| HTTP local `/health/live` | `{"status":"ok"}` | Après redéploiement |
| HTTP local `/version` | Einstein Core `0.1.0`, `production` | Après redéploiement |
| HTTPS `/health/ready` depuis le Mac | `{"status":"ready"}` | Après redéploiement |
| DNS `router.chantevigne.com` via `192.168.1.56` | `192.168.1.2` | Après redéploiement |
| HTTP local `/health/ready` | `{"status":"ready"}` | Avant redéploiement |
| HTTPS readiness LAN, VPN déconnecté | `{"status":"ready"}` | Avant redéploiement |
| HTTPS readiness via VPN | `{"status":"ready"}` | Avant redéploiement |
| HTTPS readiness depuis la connexion externe testée | HTTP 403, nginx | Avant redéploiement |
| Mémoire instantanée | 47,21 Mio / 256 Mio (18,44 %) | Avant redéploiement |
| CPU instantané | 0,25 % | Avant redéploiement |

L'en-tête Date du contrôle externe est `Fri, 16 Oct 2026 21:39:04 GMT`, soit
23:39:04 en Europe/Zurich. Le HTML Synology « page introuvable » accompagnait
le HTTP 403. Le point d'entrée HTTPS public répond mais refuse cette requête.
Ce contrôle ciblé ne constitue pas un audit de tous les ports, routes ou IPv6.
Les règles DSM n'ont pas été modifiées pendant cette séquence.

## Limites et suivi d'exploitation

- Les sorties finales ne contiennent pas le détail complet du build Core ni
  une preuve de provenance de l'image ; le commit cité identifie le clone
  utilisé pour le déploiement.
- Le contrôle externe et les mesures de ressources n'ont pas été rejoués après
  redéploiement. Les mesures instantanées ne valident pas une tenue en charge.
- La cause de l'arrêt du 14 octobre reste à investiguer si l'incident se répète.
- Compléter le `.env` Pi-hole NAS avec `DATA_DIR` avant d'utiliser la sauvegarde.
- La sauvegarde/restauration Pi-hole et la planification de synchronisation DHCP
  restent à valider séparément ; voir la [procédure Pi-hole](../pihole-operations.md).

Ces points restent visibles au suivi d'exploitation. Le Sprint 4 peut porter
sur une première fonctionnalité Maison sans ajout d'infrastructure préalable.
