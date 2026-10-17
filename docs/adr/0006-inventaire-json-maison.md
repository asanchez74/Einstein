# ADR-0006 — Inventaire Maison déclaratif JSON

- **Statut :** accepté pour l'implémentation locale, déploiement à valider
- **Date :** 17 octobre 2026

## Besoin

Consulter un petit inventaire connu en lecture seule, sans découverte réseau,
écriture concurrente ni historique. Une base de données n'apporterait pas
ici de fonction nécessaire.

## Décision

Charger un fichier JSON au démarrage, valider les équipements et l'unicité
des identifiants, puis exposer liste et détail depuis un instantané en mémoire.
Un fichier absent, illisible ou invalide empêche le démarrage. Les erreurs
ne reproduisent pas le contenu du catalogue.

Le module Maison appartient au monolithe FastAPI. Une fabrique d'application
permet d'isoler les catalogues des tests. Aucun service supplémentaire n'est ajouté.

## Conséquences

Le Core dépend désormais d'un fichier externe à sauvegarder. Sur le NAS,
le répertoire est monté en lecture seule et la configuration indique le
chemin interne. Les mises à jour demandent un redémarrage. L'exemple versionné
sert au développement ; il ne constitue pas une découverte du réseau réel.

Réévaluer le stockage uniquement avec un besoin d'écriture, de concurrence
ou d'historique démontré. Les sources DHCP et DNS restent indépendantes.
