# ADR-0011 — Interface web et authentification

- **Statut :** acceptée, implémentation en cours
- **Date :** 19 octobre 2026

## Contexte

Einstein n'est utilisable qu'avec `curl`, et ses routes n'ont aucune
authentification : tout appareil du LAN ou du VPN peut lire l'inventaire,
poser des questions consommant le forfait Plus et obtenir des extraits de
documents personnels (contrats, certificat de salaire). Le Sprint 6 a rendu
cette exposition concrète. Le propriétaire est l'unique utilisateur.

## Décision

### Authentification

Un compte unique protégé par un mot de passe propre à Einstein.

- Empreinte du mot de passe calculée avec `hashlib.scrypt` de la bibliothèque
  standard (sel aléatoire, paramètres stockés avec l'empreinte), conservée
  dans un fichier secret monté en lecture seule, hors Git. Le mot de passe
  n'est jamais stocké ni journalisé.
- Une commande génère l'empreinte en lisant le mot de passe sans écho
  (`getpass`), pour qu'il n'apparaisse ni à l'écran ni dans l'historique.
- Session côté serveur, en mémoire : jeton aléatoire de 256 bits dans un
  cookie `HttpOnly`, `Secure`, `SameSite=Strict`, durée absolue de 12 heures.
  Un redémarrage du Core déconnecte ; aucune base de sessions n'est ajoutée.
- Échecs de connexion limités : au-delà de cinq échecs en quinze minutes, la
  connexion répond 429 jusqu'à la fin de la fenêtre. Comparaison à temps constant.
- Toutes les routes `/api/` et l'interface exigent une session, sauf la
  connexion elle-même. `/health/live`, `/health/ready` et `/version` restent
  ouvertes pour le healthcheck Docker. La documentation OpenAPI interactive
  est désactivée lorsque l'authentification est active.
- Les requêtes qui modifient l'état ou consomment le forfait (POST) exigent
  `Content-Type: application/json` ; combiné à `SameSite=Strict`, cela écarte
  les soumissions de formulaires inter-sites.

L'authentification s'active par configuration et devient obligatoire dans la
stack Compose ; sans fichier d'empreinte valide, les routes protégées
répondent 503 et le Core reste sain.

### Interface

Une page unique servie par le Core, en HTML, CSS et JavaScript sans
framework, sans étape de construction ni ressource externe. FastAPI sert ces
fichiers statiques ; aucune dépendance n'est ajoutée. En-têtes :
`Content-Security-Policy` limitée à `'self'`, `frame-ancestors 'none'`,
`Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`.

Fonctions de la première version :

1. connexion et déconnexion ;
2. recherche documentaire : résultats avec source, page, extrait et mention OCR ;
3. questions sur l'inventaire (forfait Plus), avec les erreurs 429/502/504 lisibles ;
4. consultation de l'inventaire Maison ;
5. ouverture du document source d'un résultat.

### Ouverture des documents sources

Nouvelle route `GET /api/v1/documents/fichier?source=…`. Seules les sources
présentes dans l'index courant sont servies : le chemin demandé n'est jamais
interprété librement, ce qui exclut la traversée de répertoires et l'accès
aux fichiers non indexés (signature, pièce d'identité). Le fichier est ouvert
sans suivre les liens symboliques, comme pour l'indexation. Les PDF sont
affichés dans le navigateur (`inline`), les autres formats téléchargés
(`attachment`). Taille plafonnée aux limites d'indexation (50 MiB).

## Conséquences

Les scripts `curl` existants devront d'abord se connecter. Le mot de passe
est la seule protection en LAN/VPN : il doit être long et propre à Einstein.
Les sessions en mémoire conviennent à un utilisateur et un processus ; un
second utilisateur ou plusieurs processus imposeraient une autre décision.
Un PDF affiché dans le navigateur est interprété par son lecteur intégré.
L'authentification ne chiffre pas les données au repos sur le NAS.

## Alternatives écartées

- Compte Synology via SSO Server (OpenID Connect) : configuration DSM et code
  OIDC supplémentaires pour un seul utilisateur.
- Passkeys : sûres mais plus complexes, et récupération délicate.
- Authentification au niveau du reverse proxy DSM : non prise en charge
  nativement sans composant supplémentaire.
- Framework d'interface (React, Vue) : étape de construction et dépendances
  sans besoin démontré.
