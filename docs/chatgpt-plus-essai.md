# Essai du forfait ChatGPT Plus

## État

Le propriétaire souhaite essayer son forfait Plus avant toute activation de
la facturation API. L'adaptateur OpenAI par clé est conservé mais désactivé.
L'outil de connexion teste uniquement l'identité et le catalogue de modèles.
L'adaptateur Plus est désormais branché à la route HTTP pour une activation
locale explicite ; le premier essai réel est décrit plus bas.
La connexion locale et l'accès au catalogue des modèles du compte ont réussi
le 17 octobre 2026. Les preuves et les limites sont consignées dans le
[suivi du Sprint 5](sprints/sprint-5-questions-inventaire.md).

## Connexion sur le Mac

Installer les dépendances optionnelles depuis la racine :

```bash
python -m pip install -e '.[dev,chatgpt]'
python -m einstein_core.ai.chatgpt_login
```

Le navigateur présente la connexion et le consentement. Vérifier le nom
Einstein et la permission d'utiliser le forfait ChatGPT. Aucun abonnement
supplémentaire ni clé API n'est fourni par cet outil. Un refus ou une
incompatibilité arrête le parcours sans basculement vers l'API payante.

Le callback écoute uniquement sur `127.0.0.1` avec un port éphémère et une
expiration de cinq minutes. Le parcours utilise PKCE, état et nonce frais.
L'identité est validée par signature JWKS, issuer, audience, expiration,
nonce et sujet ; les scopes d'utilisation du forfait sont vérifiés.

Les identifiants d'hôte et jetons sont enregistrés sous
`~/.config/einstein/chatgpt/`, dossier 0700, fichiers atomiques 0600. Aucun
code OAuth ou jeton n'est affiché ou journalisé. Les reconnexions réutilisent
l'identifiant client émis et l'hôte ; le changement de compte est refusé
pour ce prototype à un seul compte. Ne pas transférer ces fichiers dans le
dépôt, les logs ou la conversation.

L'outil liste les modèles accessibles à ce compte via `/v1/models`.
L'accès effectif dépend du consentement et du compte ; une connexion seule
ne prouve pas le succès d'une génération. Il ne garantit pas l'éligibilité
de l'intégration NAS finale.

## Différences avec l'adaptateur API existant

Pour l'utilisation du forfait, la documentation impose `store=false` et
`stream=true`, ainsi qu'un modèle issu du catalogue du compte.
`max_output_tokens` n'est pas accepté sur ce parcours. L'adaptateur par clé
actuel ne doit donc pas recevoir simplement un jeton Plus à la place de sa clé.

Le streaming jusqu'à l'événement terminal, le renouvellement sérialisé par
verrou fichier et les limites locales sont implémentés. Les refus, erreurs
de quota et flux incomplets produisent une erreur normalisée, sans réponse
partielle et sans repli payant. La révocation depuis Einstein et le stockage
NAS restent à préparer. Ne pas promettre un plafond
de tokens serveur lorsqu'il n'est pas pris en charge par ce parcours.

Le choix proposé de `gpt-5.4-mini` pour l'API par clé ne s'applique pas
au catalogue Plus ; sélectionner un modèle effectivement retourné au compte.
Claude reste un fournisseur futur, sans intégration anticipée.

## NAS et suivi

L'essai est local au Mac. Aucun jeton n'est copié au NAS et aucune configuration
DSM n'est modifiée. Un futur déploiement devra gérer un identifiant d'hôte NAS
propre, le transfert sécurisé et la rotation des sessions, selon le guide
self-hosted. Le service gère le refresh ; l’outil ne fournit pas encore de déconnexion distante.
Les autorisations peuvent être retirées dans les paramètres ChatGPT.

## Sources officielles vérifiées le 17 octobre 2026

- [Applications locales et forfait ChatGPT](https://developers.openai.com/siwc/token-sharing-open-source)
- [Inscription et connexion](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Modèles et inférence](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Limites du parcours](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Hébergement distant](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms)

## Utiliser la route localement

Après installation de l'extra `chatgpt` et connexion validée, depuis le Mac :

```bash
export EINSTEIN_AI_ENABLED=true
export EINSTEIN_AI_PROVIDER=chatgpt
export EINSTEIN_AI_MODEL=gpt-6-luna
export EINSTEIN_AI_CHATGPT_CREDENTIALS_FILE="$HOME/.config/einstein/chatgpt/credentials.json"
python -m uvicorn einstein_core.main:app --host 127.0.0.1 --port 8000
```

Dans un autre terminal, chaque requête ci-dessous transmet la question et le
catalogue à OpenAI et consomme les limites de l'abonnement :

```bash
curl --fail --show-error http://127.0.0.1:8000/api/v1/maison/questions \
  -H 'Content-Type: application/json' \
  -d '{"question":"Quelle est l’adresse du NAS ?"}'
```

Le modèle doit être issu du catalogue de ce compte. Le 17 octobre 2026,
`gpt-6-luna` a répondu avec HTTP 200 et l'adresse `192.168.1.3`, via la route
locale en `TestClient`, le service métier et l'adaptateur Plus réels.
Le résultat confirme un premier cas nominal ; il ne valide pas à lui seul
la qualité sur des questions inconnues ou des injections.

`EINSTEIN_AI_MAX_OUTPUT_CHARS` borne le texte reçu (8192 caractères par défaut).
Dépasser la limite ferme le flux et rejette la réponse, sans garantir un plafond
de tokens consommés côté fournisseur. Le délai total inclut le renouvellement.
Le refresh est atomique et sérialisé ; une session révoquée exige une reconnexion.
Aucun basculement vers une clé API n'est implémenté.

La stack NAS de base reste sans IA ; le complément `compose.openai.yaml`
concerne uniquement l'authentification par clé API et ne doit pas être utilisé
pour monter une session Plus. La session a ensuite été transférée au NAS pour le déploiement décrit dans
le suivi du Sprint 5. Ne plus utiliser la copie Mac pour son renouvellement.

## Préparation du déploiement Plus sur le NAS

Le complément `compose.chatgpt.yaml` est distinct du complément par clé API.
Il active l'installation de l'extra `chatgpt` à la construction de l'image.
Ne jamais combiner ces deux compléments.

Préparer dans le `.env` NAS, après commit et mise à jour du dépôt :

```dotenv
COMPOSE_FILE=compose.yaml:compose.chatgpt.yaml
EINSTEIN_AI_ENABLED=false
EINSTEIN_AI_MODEL=gpt-6-luna
CHATGPT_SESSION_DIR=/volume1/docker/einstein/secrets/einstein-core/chatgpt
EINSTEIN_AI_TIMEOUT_SECONDS=45
EINSTEIN_AI_MAX_OUTPUT_CHARS=8192
```

Le dossier de session doit exister, appartenir à `10001:10001` et être en 0700.
Il est monté sur `/session` en écriture pour le refresh atomique et le verrou ;
la racine du conteneur et le montage du catalogue restent en lecture seule.
Le complément ne crée pas de dossier manquant et l'activation reste false.

Construire l'image, puis initialiser un identifiant propre au NAS avec le
module fourni, depuis `compose/einstein-core` :

```bash
sudo docker compose --env-file .env build api
sudo docker compose --env-file .env run --rm --no-deps \
  api python -m einstein_core.ai.chatgpt_session --directory /session
```

Le transfert de `credentials.json` doit être fait par SSH vers un emplacement
privé temporaire du NAS. Aucun transfert n'est exécuté par ces commandes.
Le fichier temporaire doit être 0600 et lisible par l'UID 10001. L'import peut
ensuite être lancé avec ce fichier monté en lecture seule :

```bash
# Remplacer le chemin source par le fichier privé réellement transféré.
sudo docker compose --env-file .env run --rm --no-deps \
  -v /chemin/prive/credentials.json:/import/credentials.json:ro \
  api python -m einstein_core.ai.chatgpt_session \
  --directory /session --import-from /import/credentials.json
```

L'import conserve l'identifiant d'hôte NAS, écrit en 0600 et refuse de remplacer
une session existante. Il ne vérifie pas en ligne la validité de l'accès ;
l'essai d'inférence NAS est un contrôle séparé. Ne pas copier le `host.json`
du Mac au NAS.

Après transfert, le NAS doit devenir l'unique processus qui renouvelle cette
session : ne plus utiliser la copie Mac en parallèle, car le refresh token
est rotatif. Ne pas révoquer cette session depuis le Mac pour la « nettoyer » :
cela invaliderait aussi la session transférée. Prévoir un nettoyage privé des
copies temporaires après vérification, sans les verser dans la sauvegarde
ordinaire du catalogue.

Valider Compose et les permissions avant de fixer `EINSTEIN_AI_ENABLED=true`
et déployer avec `stack-up.sh einstein-core`. En cas d'échec, sélectionner
`COMPOSE_FILE=compose.yaml` puis redéployer : aucun repli payant n'est effectué.
Le build, l’import et un premier test HTTPS NAS ont réussi ; voir le
[suivi Sprint 5](sprints/sprint-5-questions-inventaire.md) pour les contrôles
restants.
