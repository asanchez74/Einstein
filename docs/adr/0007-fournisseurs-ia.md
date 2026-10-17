# ADR-0007 — Interface fournisseur IA et premier adaptateur OpenAI

- **Statut :** accepté pour l’implémentation locale, déploiement à valider
- **Date :** 17 octobre 2026

## Besoin

Interroger l'infrastructure décrite dans l'inventaire, avec OpenAI en premier
et Claude (Anthropic) ensuite, sans coupler le domaine Maison à un SDK.

## Décision

Une interface asynchrone `AnswerProvider` reçoit instructions, contexte et
question, retourne un objet `Answer` propre au projet et expose une fermeture
explicite des ressources. Les erreurs fournisseur et timeout sont normalisées.
Le service Maison préparera le contexte ; l'adaptateur ne lit aucun fichier.

`OpenAIProvider` utilise le SDK officiel `openai==3.33.0` et Responses API.
Modèle et clé sont explicites, aucun modèle n'est choisi par défaut.
Les appels utilisent `store=false`, sans historique, outils ou retries.
Le délai total et le plafond de tokens de sortie sont bornés. Le catalogue
est transmis comme donnée dans un message utilisateur, distinct des
instructions. Cette séparation ne garantit pas seule la résistance aux
injections ; les évaluations métier restent nécessaires.

Les refus, réponses incomplètes et réponses vides sont rejetés. Aucun corps
d'erreur distant n'est réexposé par les exceptions du projet.

## Conséquences et limites

Une dépendance SDK est ajoutée. Sa contrainte `httpx2>=2.12.0` impose d'aligner
la dépendance de tests, fixée ici à `2.13.1`. Les tests utilisent le vrai SDK
avec un transport HTTP simulé et une fausse clé, sans requête distante.

L’API HTTP est intégrée, désactivée par défaut. Le service métier prépare
le catalogue ; question, contexte et concurrence sont bornés. La lecture
locale d’une clé fichier est implémentée. Le montage Compose du secret est préparé dans un complément optionnel ;
sa validation NAS, l’évaluation réelle et le déploiement restent à réaliser. Le futur
adaptateur Anthropic n'est pas implémenté par anticipation.

Les données envoyées quittent le NAS : `store=false` ne garantit pas une
absence totale de rétention fournisseur. L'activation et le contexte transmis
seront explicités dans le guide d'exploitation avant le premier appel réel.

## Sources officielles

- [Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
- [Contrôles de données](https://developers.openai.com/api/docs/guides/your-data)

## Extension : forfait ChatGPT Plus

À la demande du propriétaire, le premier essai réel utilise le forfait Plus,
avec l'interface métier existante et un adaptateur `ChatGPTProvider` distinct.
OAuth/OIDC, modèles du compte, `store=false` et streaming sont utilisés ;
`max_output_tokens` est omis. La sortie est bornée localement en caractères,
sans promesse de plafond de consommation serveur.

La session est conservée hors Git en fichiers privés. Un verrou fichier
sérialise le refresh, puis le fichier est remplacé atomiquement avec les deux
jetons mis à jour. Aucun repli par clé API n'est effectué en cas de quota,
révocation ou erreur. Le premier essai local `gpt-6-luna` a réussi.
La session Plus n'est pas déployée sur le NAS.

Pour le futur déploiement Plus, un complément Compose installe les dépendances
OAuth optionnelles. Seul le répertoire privé de session est inscriptible pour
la rotation ; le catalogue et la racine restent en lecture seule. L'import
préserve l'identifiant d'hôte NAS. Une session transférée ne doit pas être
renouvelée simultanément par le Mac et le NAS. Ce déploiement reste à valider.

## Extension : Claude (Anthropic) reporté — 17 octobre 2026

Le propriétaire dispose d'un abonnement Claude Max et souhaitait l'utiliser
comme le forfait Plus. Les conditions d'Anthropic l'excluent : la connexion
par abonnement (Free, Pro, Max) est réservée aux applications Anthropic,
et les applications tierces doivent utiliser une clé API Claude Console ou
un fournisseur cloud. Collecter, stocker ou relayer des jetons de session
Claude.ai n'est pas autorisé. Aucun équivalent de « Sign in with ChatGPT »
n'existe donc pour Einstein.

Faire tourner Claude Code sur le NAS avec le compte Max pour servir l'API
est écarté : usage ambigu au regard des conditions, Node et processus lourd
sur le DS918+. Le propriétaire choisit de ne pas ouvrir de facturation API
Anthropic pour l'instant : l'adaptateur Claude est reporté. S'il est repris,
ce sera par clé API fichier, sur le modèle de l'adaptateur OpenAI par clé,
avec plafond de dépense défini dans la Console et sans repli automatique.

L'orchestrateur choisissant un fournisseur selon la tâche est également
reporté jusqu'à disposer de deux fournisseurs opérationnels ; il fera
l'objet d'une ADR distincte.

Source vérifiée le 17 octobre 2026 :
[Claude Code — Legal and compliance, Authentication and credential use](https://code.claude.com/docs/en/legal-and-compliance)
