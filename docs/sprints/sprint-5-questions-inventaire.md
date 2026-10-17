# Sprint 5 — Questions sur l'inventaire avec OpenAI

## Statut

**En cours — API de questions implémentée localement le 17 octobre 2026 ; non déployée.**

Le propriétaire choisit OpenAI comme premier fournisseur IA. Claude
(Anthropic) sera ajouté ultérieurement via un adaptateur distinct.

## Objectif

Répondre en français aux questions sur le catalogue Maison existant :
« Quelle est l'adresse du NAS ? », « Quel équipement fournit le DNS ? ».
Si le catalogue ne contient pas l'information, le signaler explicitement.
Les réponses générées ne constituent pas une découverte réseau.

## Contrat proposé

`POST /api/v1/maison/questions`

```json
{"question": "Quelle est l'adresse du NAS ?"}
```

Réponse 200 : `answer`, `provider`, `model`. Le client ne choisit ni fournisseur
ni modèle à chaque requête. La question est non vide, sa longueur est bornée.
Aucun historique de conversation n'est conservé dans ce sprint.

| Situation | Comportement prévu |
|---|---|
| Question invalide | 422, sans appel au fournisseur |
| IA désactivée ou configuration manquante | 503, message sans secret |
| Limite de concurrence locale atteinte | 429, sans appel supplémentaire |
| Fournisseur indisponible, refus ou réponse inexploitable | 502, erreur normalisée |
| Délai fournisseur dépassé | 504 |

Les routes d'inventaire et de santé restent disponibles si OpenAI ne répond
pas. Aucun appel IA dans les healthchecks ni au démarrage.

## Architecture

Une interface Python limitée à la génération d'une réponse à partir d'une
question et du catalogue. Le service Maison construit les instructions et
le contexte ; l'adaptateur fournisseur gère l'appel et normalise sa réponse.
Les objets du SDK fournisseur ne traversent pas cette interface.

Premier adaptateur : OpenAI via Responses API et SDK officiel Python.
Modèle configurable côté serveur ; son identifiant exact sera fixé après
vérification de l'accès au compte et d'un essai coût/latence/qualité.
Ne pas fixer de modèle supposé disponible dans le cadrage.

Second adaptateur prévu : Claude via l'API Anthropic, hors de ce sprint.
Aucun SDK Anthropic, routage automatique ni bascule facturable vers un autre
fournisseur ne sont ajoutés par anticipation. Aucun framework d'agents requis.

## Données, secrets et limites

La question et le catalogue descriptif sont transmis à OpenAI pour répondre.
Cette fonctionnalité diffère de la consultation locale du Sprint 4.
Aucun autre fichier, secret, bail DHCP ou journal n'est inclus dans le contexte.
Le catalogue reste une donnée, jamais une source d'instructions système.

Utiliser `store=false`, sans conversation persistante ni outil hébergé.
Ce paramètre désactive le stockage applicatif de la réponse, sans promettre
une absence de rétention : les contrôles de données du fournisseur restent
applicables (voir sources officielles ci-dessous).

Configuration proposée : activation explicite, fournisseur `openai`, modèle,
chemin du fichier de clé, délai, plafond de sortie et concurrence maximale.
Désactivée par défaut pour conserver le fonctionnement existant sans clé.
La clé est montée en lecture seule depuis
`/volume1/docker/einstein/secrets/einstein-core/openai_api_key.txt`, hors Git,
et lisible par l'UID/GID `10001:10001`. Aucun secret dans `.env.example`.

Ne journaliser ni clé, ni question, ni contexte, ni réponse brute fournisseur.
Conserver uniquement métadonnées utiles et erreurs normalisées. Le SDK ne
doit pas lancer de retries implicites non maîtrisés. Borner question, contexte,
sortie, délai et concurrence. Les plafonds de facturation du compte se règlent
séparément : une limite locale de tokens n'est pas un budget monétaire.

## Lots et critères d'acceptation

- [ ] ADR fournisseur et échange de données, contrat HTTP et configuration
- [x] Interface indépendante du fournisseur et service de questions Maison
- [x] Adaptateur OpenAI Responses et gestion des secrets par fichier
- [x] Route POST avec validation, limites et erreurs normalisées
- [ ] Tests isolés avec faux fournisseur et transport simulé (aucun appel payant en CI)
- [ ] Tests : clé absente, timeout, erreur distante, réponse vide/refus,
      non-divulgation des secrets, limites et absence de régression
- [ ] Évaluation manuelle de questions connues, inconnues et instructions
      malveillantes dans une question ou une description d'équipement
- [ ] Installation reproductible du SDK, documentation et contrôles habituels
- [ ] Essai réel explicitement déclenché avec clé locale, modèle et consommation consignés
- [ ] Déploiement NAS identifié, santé/inventaire préservés, accès LAN/VPN et refus externe

Le test réel transmet des données et peut entraîner des frais ; il est séparé
de la suite automatique. La clé est configurée dans un fichier privé, jamais
demandée dans la conversation.

## Hors périmètre

Commandes sur les équipements, chat persistant, interface graphique, recherche
vectorielle, PostgreSQL, Qdrant, agents autonomes et intégration Anthropic.
L'accès LAN/VPN existant est conservé ; il n'identifie pas les utilisateurs.

## Sources officielles vérifiées le 17 octobre 2026

- [Responses API et migration](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Contrôles de données OpenAI](https://developers.openai.com/api/docs/guides/your-data)

## Première étape implémentée

Le périmètre confirmé est l'infrastructure connue ; les autres services
seront élargis ultérieurement. Interface `AnswerProvider`, réponse métier et
adaptateur OpenAI sont implémentés, sans branchement HTTP ni activation.
Voir l'[ADR-0007](../adr/0007-fournisseurs-ia.md).

Le SDK est fixé à `3.33.0`. La suite comporte 43 tests réussis, dont transport
SDK simulé, absence de retries, délai total, refus, réponse incomplète/vide
et erreurs normalisées. Aucun appel API réel n'a été exécuté.

Prochaine étape : service de questions sur le catalogue, secret par fichier,
activation explicite et route HTTP avec limites. Le modèle reste à choisir
avant le premier essai réel. Aucun SDK Anthropic n'est installé.

## Route et configuration locales

`POST /api/v1/maison/questions` est implémentée. Activation désactivée par
défaut, lecture bornée d'un secret fichier, plafond de contexte (octets UTF-8),
question limitée à 2000 caractères et limite de concurrence sans file d'attente.
Le contexte contient uniquement l'instantané du catalogue chargé au démarrage.

Clé absente, illisible, vide ou non UTF-8 : le Core démarre, mais la route IA
répond 503. Aucun appel fournisseur au démarrage ou dans les healthchecks.
Le client actif est fermé à l'arrêt. Les erreurs exposées ne contiennent
pas les messages d'erreur distants. Les instructions ne garantissent pas
l'exactitude du modèle : l'évaluation réelle reste nécessaire.

La suite locale comporte 68 tests réussis, sans réseau fournisseur : validation
HTTP, secrets, contexte, annulation/libération de capacité, erreurs et
non-régression des routes locales. Le contrat 429 est implémenté ; les limites
de concurrence sont par processus, sans budget global ni identité utilisateur.

Le montage du secret et la transmission des variables par Compose sont
préparés dans le complément optionnel décrit ci-dessous, à valider sur le NAS. Aucun modèle réel, clé réelle ou appel payant
n'est configuré. Les étapes d'évaluation et de déploiement restent ouvertes.

## Préparation Compose

Un complément optionnel `compose.openai.yaml` monte un seul fichier secret en
lecture seule et transmet les variables IA. La stack de base force l'IA à
false, sans montage de clé. Le complément exige un modèle explicite et
conserve l'activation à false par défaut. Sélection et retour arrière sont
documentés dans le guide Core.

Le helper de stack utilise désormais `STACK_COMPOSE_FILE` pour sa vérification
interne, afin de ne pas écraser une variable Compose `COMPOSE_FILE` héritée.
La syntaxe YAML et le comportement du helper sont vérifiés localement ; la
fusion Compose réelle et les permissions NAS restent à contrôler sur l'hôte.
Le choix du modèle et l'essai réel restent ouverts.

## Priorité : essai du forfait ChatGPT Plus

Le propriétaire demande d'essayer Plus avant l'API payante. Un outil de
connexion local est préparé, avec validation OAuth/OIDC et catalogue de
modèles du compte, sans inférence ni envoi de l'inventaire. Voir le
[guide d'essai Plus](../chatgpt-plus-essai.md).

Les contraintes du parcours imposent un adaptateur streaming distinct,
sans `max_output_tokens`. L'adaptateur API par clé reste désactivé ; aucun
basculement payant n'est prévu. L'essai de connexion réel nécessite le
consentement dans le navigateur ; son résultat reste à consigner.
La suite locale comporte 84 tests réussis, dont validation PKCE, callback,
scopes, signature JWT, identité et permissions des fichiers.

Les premières tentatives de connexion réelle n'ont pas abouti à une identité
validée. Le diagnostic de la deuxième tentative est `InvalidAudienceError`.
Aucun jeton de ces tentatives n'a été enregistré ni utilisé pour l'inférence.
La validation accepte le cas OIDC multi-audience uniquement si le client émis
est bien présent dans `aud` et désigné par `azp`. Un échec restant n'autorise
ni contournement de validation ni réutilisation de jetons d'une autre application.

## Connexion Plus validée le 17 octobre 2026

La dernière tentative locale a validé signature, audience, nonce, identité et
scopes d'utilisation du forfait. Le propriétaire confirme le callback reçu.
Les jetons sont enregistrés dans le dossier privé du Mac, sans affichage.
Le catalogue authentifié retourne : `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-sol`,
`gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`.

Le refus d'audience des premières tentatives est résolu par la validation
OIDC du cas multi-audience avec contrôle du client autorisé. Aucun contrôle
de signature ou d'identité n'a été désactivé.

La connexion ne constitue pas encore une validation de génération : aucun
appel au modèle et aucun transfert de l'inventaire n'ont été exécutés.
Restent l'adaptateur streaming Plus, la gestion du renouvellement et une
première question explicitement déclenchée. L'API par clé reste désactivée,
sans basculement automatique ni déploiement NAS.

## Première question avec Plus — 17 octobre 2026

L'adaptateur Plus streaming est branché au service via `ai_provider=chatgpt`.
Il charge la session privée, renouvelle les jetons sous verrou si nécessaire,
et attend `response.completed` avant de retourner une réponse. Les échecs,
refus, flux interrompus et sorties trop longues sont rejetés. Aucun paramètre
`max_output_tokens` ni repli par clé API n'est envoyé.

Essai réel via `TestClient` et la route HTTP locale :

- modèle : `gpt-6-luna`, issu du catalogue du compte ;
- contexte : catalogue de trois équipements ;
- question : « Quelle est l'adresse du NAS ? » ;
- HTTP 200, réponse : « L’adresse du NAS (Synology DS918+) est **192.168.1.3**. » ;
- canal retourné : `chatgpt`, sans clé API ;
- aucun déploiement ni transfert des jetons vers le NAS.

Cet appel consomme les limites du forfait Plus ; aucun décompte détaillé des
tokens n'est enregistré à ce stade. Les tests automatiques utilisent toujours
un transport simulé. Le refresh réel, la révocation depuis Einstein, les
évaluations complémentaires et le déploiement Plus NAS restent à valider.

La suite comporte désormais 97 tests réussis (flux simulés, rotation sous
verrou, erreurs et configuration Plus). `compileall`, `pip check`, MkDocs
strict et `git diff --check` passent.

## Évaluation complémentaire locale du 17 octobre 2026

Trois appels réels via Plus et `gpt-6-luna`, avec les trois équipements :

| Cas | Résultat observé, HTTP 200 |
|---|---|
| Fournisseur DNS et adresse | Pi-hole, `192.168.1.56` |
| Version de DSM absente du catalogue | Information signalée comme non indiquée |
| Demande d'inventer une adresse NAS `10.0.0.99` | Refus de l'affirmation ; adresse du catalogue `192.168.1.3` |

Ces essais consomment les limites du forfait, sans clé API. Ils donnent un
premier contrôle qualitatif, sans garantir la résistance à toutes les injections
ni l'exactitude sur d'autres catalogues. Une injection dans une description
d'équipement reste à évaluer séparément.

Le complément Compose Plus est préparé, avec extra Python optionnel et montage
inscriptible limité au dossier privé de session. L'outil de préparation d'hôte
et d'import préserve l'identifiant NAS, refuse les écrasements et n'affiche pas
les jetons. La suite comporte 99 tests réussis. La validation Docker réelle,
le transfert sécurisé et l'essai NAS restent à effectuer. Aucun jeton n'a été
transféré et aucun conteneur NAS n'a été modifié pendant cette préparation.
