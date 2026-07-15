# ADR-0004 — Gestion des ressources CPU sous DSM

- **Statut :** accepté
- **Date :** 15 juillet 2026

## Contexte

Le Synology DS918+ exécute Docker Engine 24.0.2 sous DSM 7.2.2 Update 9.

Le modèle Compose initial utilisait la propriété `cpus` pour imposer un quota
CPU dur. Lors du déploiement du service de validation, Docker a retourné :

```text
NanoCPUs can not be set, as your kernel does not support CPU CFS scheduler
or the cgroup is not mounted
```

Le noyau DSM de cet hôte ne fournit donc pas le mécanisme de quota CPU CFS
attendu par Docker pour `NanoCPUs`.

## Décision

Les services Einstein n’utilisent pas la propriété Compose `cpus` sur cet hôte.

La gestion des ressources repose sur :

- `mem_limit` pour limiter strictement la mémoire ;
- `cpu_shares` pour définir une pondération CPU relative entre conteneurs.

Exemple :

```yaml
mem_limit: 512m
cpu_shares: 256
```

La valeur `cpu_shares` ne représente ni un nombre de cœurs ni un pourcentage.
Elle influence uniquement la répartition du processeur en situation de
concurrence.

## Alternatives considérées

### Conserver `cpus`

Rejeté, car le déploiement échoue sur le noyau DSM actuel.

### Utiliser `deploy.resources.limits.cpus`

Rejeté pour cet usage : cette configuration conduit au même mécanisme de quota
CPU lorsque Docker tente de l’appliquer.

### Ne définir aucune politique CPU

Rejeté comme règle générale, car une pondération relative reste utile pour
éviter qu’un service secondaire domine les autres charges du NAS.

### Modifier le noyau ou les cgroups de DSM

Rejeté : cette intervention serait non standard, fragile lors des mises à jour
DSM et contraire à l’objectif d’une infrastructure maintenable.

## Conséquences positives

- compatibilité avec le noyau DSM du DS918+ ;
- déploiement Compose fonctionnel ;
- priorité relative configurable ;
- limites mémoire strictes conservées ;
- aucune modification non supportée de DSM.

## Conséquences négatives

- absence de plafond CPU dur par conteneur ;
- un conteneur peut utiliser davantage de CPU lorsque les ressources sont
  disponibles ;
- la charge CPU doit être surveillée lors de l’introduction de services plus
  lourds.

## Réévaluation

Cette décision devra être réévaluée en cas de :

- migration vers un autre hôte ;
- mise à niveau majeure de DSM ou du noyau ;
- activation vérifiée des quotas CPU CFS ;
- ajout d’un nœud de calcul dédié à l’intelligence artificielle.
