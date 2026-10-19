# Sprint 7 — Interface web et authentification

## Statut

Cadrage validé le 19 octobre 2026 ; implémentation en cours.
Décision d'architecture : [ADR-0011](../adr/0011-interface-authentification.md).

## Objectif

Utiliser Einstein depuis un navigateur sur le LAN ou le VPN, sans `curl`,
et protéger toutes les fonctions par un mot de passe. Le propriétaire est
l'unique utilisateur.

## Choix du propriétaire

- Connexion par mot de passe propre à Einstein.
- Première version : recherche documentaire, questions sur l'inventaire,
  consultation de l'inventaire, ouverture des documents sources.

## Lots

1. **Authentification** : empreinte scrypt, commande de génération,
   sessions, limitation des échecs, protection des routes `/api/`,
   désactivation d'OpenAPI, tests.
2. **Ouverture des documents** : route limitée aux sources indexées,
   affichage PDF ou téléchargement, tests de traversée et de liens.
3. **Interface** : page unique sans framework, quatre onglets, en-têtes de
   sécurité, affichage soigné des erreurs et de l'état d'indexation.
4. **Déploiement NAS** : fichier secret, Compose, validation LAN/VPN,
   refus externe, déconnexion, échecs limités.

## Critères d'acceptation

- Sans session, toute route `/api/` répond 401, l'interface affiche la connexion.
- Santé et version restent accessibles au healthcheck.
- Le mot de passe n'apparaît dans aucun fichier, journal ni historique.
- Cinq échecs en quinze minutes bloquent temporairement la connexion.
- Un document non indexé ou un chemin arbitraire ne peut pas être ouvert.
- L'interface fonctionne sur le Mac et sur l'iPhone, sans ressource externe.
- Tests automatisés sans réseau ; suite complète, MkDocs strict, `git diff --check`.

## Hors périmètre

Plusieurs utilisateurs, rôles, SSO Synology, passkeys, historique de
conversation, téléversement de documents, application mobile.

## Lot 1 — Authentification, implémentation locale

- `einstein_core.auth` : empreinte `scrypt` (N = 2^15, r = 8, p = 1, sel de
  16 octets), vérification à temps constant, sessions en mémoire (jeton de
  256 bits, seule son empreinte SHA-256 est conservée), limite globale de
  cinq échecs en quinze minutes.
- `python -m einstein_core.auth` lit le mot de passe deux fois sans écho et
  n'écrit que l'empreinte sur la sortie standard, pour redirection vers le
  fichier secret. Douze caractères au moins.
- Routes `POST /api/v1/auth/connexion` (204, cookie `einstein_session`
  `HttpOnly`, `Secure`, `SameSite=Strict`, 12 h), `POST /api/v1/auth/deconnexion`
  et `GET /api/v1/auth/session`.
- Lorsque `EINSTEIN_AUTH_ENABLED=true` : toute route `/api/` exige une session
  (401), tout POST `/api/` exige `Content-Type: application/json` (415),
  OpenAPI et `/docs` sont coupés ; santé et version restent ouvertes.
  Empreinte absente ou invalide : connexion 503, Core sain.

Variables : `EINSTEIN_AUTH_ENABLED`, `EINSTEIN_AUTH_PASSWORD_HASH_FILE`,
`EINSTEIN_AUTH_COOKIE_SECURE` (vrai par défaut), `EINSTEIN_AUTH_SESSION_HOURS`.
Désactivée par défaut : aucun changement en production avant le lot 4.
166 tests réussis, dont 13 pour l'authentification.

## Lot 2 — Ouverture des documents sources, implémentation locale

`GET /api/v1/documents/fichier?source=<référence relative>` sert un fichier
uniquement si cette référence figure dans l'index courant. Le fichier est
rouvert composant par composant depuis la racine montée, sans suivre aucun
lien ; composants vides, cachés, `.` et `..` sont refusés. Taille plafonnée à
50 MiB. PDF en `inline`, `.docx`, `.txt` et `.md` en `attachment`, nom encodé
selon RFC 5987, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`.

Un document absent de l'index (scan sans texte, fichier caché, chemin
arbitraire, répertoire) répond 404 sans détail. Une source remplacée par un
lien, ou dont un répertoire parent devient un lien, après l'indexation est
refusée. Avec l'authentification active, la route exige une session.
178 tests réussis, dont 12 pour cette route.
