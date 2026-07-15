# Smoke test Docker

Ce service valide le socle Docker d'Einstein.

## Fonctions testées

- déploiement avec Docker Compose ;
- image à version fixe ;
- publication sur l'interface locale uniquement ;
- volume persistant ;
- exécution avec l'UID et le GID de l'utilisateur `tonio` ;
- système de fichiers du conteneur en lecture seule ;
- suppression des capacités Linux ;
- healthcheck HTTP ;
- limite mémoire et pondération CPU ;
- rotation des journaux.

## Accès

Depuis le NAS :

```bash
curl http://127.0.0.1:18080
```

Depuis le Mac à travers un tunnel SSH :

```bash
ssh -L 18080:127.0.0.1:18080 einstein
```

Puis ouvrir :

```text
http://127.0.0.1:18080
```

## Données persistantes

Le conteneur écrit sa date de démarrage dans :

```text
/volume1/docker/einstein/data/smoke-test/started-at.txt
```
