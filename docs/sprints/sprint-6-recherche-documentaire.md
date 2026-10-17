# Sprint 6 — Recherche documentaire locale

## Statut

En cours : mode local déployé sur le NAS et validé sur un corpus synthétique
le 17 octobre 2026 ; corpus réel et mode OpenAI non déployés. Les validations
restantes du Sprint 5 restent ouvertes ; le redémarrage NAS est reporté.

## Périmètre confirmé

Dossier NAS `/volume1/Documents/03_Tonio/Travail` ; formats PDF, Word `.docx`, texte `.txt`
et Markdown `.md`. Recherche locale uniquement, avec extraits et sources.
Le chemin `./03_Tonio/Travail/` est interprété relativement à
`/volume1/Documents`. Seul ce sous-dossier et ses descendants visibles seront
montés dans le conteneur ; les autres dossiers de Documents restent hors corpus.
Voir l'[ADR-0009](../adr/0009-recherche-documentaire-locale.md).

## Livrables

- [x] Extraction bornée et isolée des trois familles de formats
- [x] Recherche lexicale avec référence relative, passage et page PDF
- [x] API désactivée par défaut, indépendante de la configuration IA
- [x] Complément Compose en lecture seule
- [x] Essai vision Plus sur une image synthétique
- [x] Traitement documentaire OpenAI avec cache local et limites (implémenté localement, non déployé)
- [x] Validation NAS sur corpus synthétique : montage, droits, ressources, démarrage
- [x] Validation NAS sur un sous-dossier réel (`Lombard Odier`)
- [ ] Couverture des PDF scannés (OCR, lot suivant)
- [ ] Dossier `Travail` complet (index persistant, si le besoin est confirmé)
- [x] Accès LAN et refus externe de la nouvelle route
- [x] Accès via VPN de la nouvelle route
- [x] Évaluation de pertinence sur quelques recherches choisies

Aucun document réel n'a été consulté ni transféré pendant l'implémentation.
L'interface pour interagir facilement avec Einstein sera le chantier suivant.

## API

`POST /api/v1/documents/recherche`

```json
{"query":"assurance habitation","limit":5}
```

Réponse : `indexed_at`, `indexed_files`, `skipped_files`, `partial`, `results`.
Chaque résultat contient `source`, `page` (ou null), `passage`, `excerpt`,
`score` (occurrences des mots). Un seul résultat par document : son meilleur
passage. Maximum 20 résultats, requête de 1 à 300
caractères. Aucun résultat : liste vide ; entrée invalide : 422 ; module
indisponible/désactivé : 503. Une requête composée uniquement de ponctuation
ne contient aucun mot et retourne une liste vide.

## Préparation du déploiement

Après revue, commit et push, mettre à jour le clone NAS puis reconstruire
l'image. Dans le `.env` runtime, sélectionner les compléments souhaités :

```dotenv
COMPOSE_FILE=compose.yaml:compose.chatgpt.yaml:compose.documents.yaml
DOCUMENTS_DIR=/volume1/Documents/03_Tonio/Travail
EINSTEIN_DOCUMENTS_ENABLED=true
```

Le conteneur lit avec UID/GID `10001:10001`. Vérifier les permissions du dossier
sélectionné ; ne pas appliquer de changement récursif global aux documents.
Un sous-dossier dédié est préférable si le corpus dépasse les limites ou
contient des fichiers qui ne doivent pas être consultables via Einstein.
Le chemin source ne peut pas être un lien symbolique.

Utiliser les scripts habituels pour déployer puis vérifier la santé et :

```bash
curl --fail --show-error --connect-timeout 5 --max-time 10 \
  -H 'Content-Type: application/json' \
  -d '{"query":"assurance","limit":5}' \
  https://einstein.chantevigne.com/api/v1/documents/recherche
```

Consulter `partial` et les compteurs avant d'interpréter une absence de résultat.
Le total des fichiers exclus concerne les candidats supportés qui échouent ;
les formats non supportés, fichiers cachés et liens ignorés n'y figurent pas.

Retour arrière : mettre `EINSTEIN_DOCUMENTS_ENABLED=false` et redéployer ;
retirer aussi le complément si le montage n'est plus souhaité. Aucun fichier
source n'est modifié par Einstein. Pas d'accès à OpenAI pour cette recherche.

## Vérifications locales

119 tests passent, sans réseau : extraction réelle sur PDF et DOCX synthétiques,
texte accentué, références, recherche et limites HTTP, instantané, liens exclus,
fichiers cachés, PDF chiffrés ou sans texte, plafond de pages, fichier trop gros,
XML avec DTD, budget de parcours et timeout d'extraction simulé. Les routes
existantes restent disponibles lorsque le dossier documentaire est absent.
`compileall`, `pip check`, MkDocs strict et `git diff --check` passent.

Le YAML du complément est vérifié. Docker n'est pas disponible sur le Mac :
la fusion Compose et le plafond mémoire de l'extracteur sous DSM restent à
valider sur le NAS. Aucun fichier utilisateur ni corpus NAS n'a été lu.

## Lot suivant confirmé — OCR local des PDF scannés

Le propriétaire ajoute l'OCR au périmètre. Il n'est pas implémenté dans le
lot actuel : les PDF sans texte restent écartés par le lecteur existant.

Traitement prévu :

1. Extraire le texte existant et repérer les pages sans texte exploitable.
2. Reconnaître ces pages en français avec Tesseract, localement, dans un
   traitement séparé du démarrage et des requêtes HTTP.
3. Conserver le texte dérivé dans un cache runtime distinct des originaux,
   avec référence au fichier, empreinte de version et numéro de page.
4. Rendre les passages disponibles à la recherche, en indiquant leur origine
   OCR et les pages non traitées ou en erreur.

Les originaux restent montés en lecture seule depuis
`/volume1/Documents/03_Tonio/Travail`. Aucun envoi à OpenAI. Les images isolées,
l'écriture manuscrite et les autres langues sont hors de ce premier lot OCR.
Une page mixte avec du texte extractible et une image textuelle peut nécessiter
un traitement supplémentaire ; la détection initiale ne garantit pas sa couverture.

Un seul fichier sera traité à la fois, avec limites de pages, résolution,
délai et mémoire. L'enveloppe mémoire et la méthode de rendu PDF seront fixées
après un essai sur document synthétique, sans augmenter le budget du Core par
anticipation. L'OCR ne doit pas utiliser les trois secondes prévues pour
l'extraction actuelle : ce sera un chemin distinct, activé explicitement.

Avant intégration : tester un PDF entièrement scanné, un PDF mixte, un fichier
chiffré, un dépassement de délai, la préservation des originaux et
l'invalidation du cache après modification ou suppression d'une source.
Mesurer ensuite ressources et qualité sur un petit échantillon choisi du NAS.

Références vérifiées le 17 octobre 2026 :

- [Tesseract — langues disponibles, dont `fra`](https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html)
- [OCRmyPDF — traitements et limites](https://ocrmypdf.readthedocs.io/en/latest/advanced.html)

Tesseract est le moteur envisagé ; le choix d'OCRmyPDF ou d'un rendu PDF
minimal reste ouvert. Aucun binaire OCR ni service supplémentaire n'a été
installé pour ce cadrage.

## Essai vision OpenAI autorisé

Le propriétaire demande un essai de transcription par IA et exprime sa
préférence pour un traitement OpenAI de tout le corpus choisi si l'essai
est concluant. Cela concerne uniquement `/volume1/Documents/03_Tonio/Travail`,
pas les autres documents du NAS. Ce changement de direction reste à intégrer
à l'architecture après mesure du résultat ; aucun envoi massif n'est activé.

`scripts/ocr-openai-probe.py` génère un PNG synthétique en mémoire et transmet
uniquement cette image via Plus, au modèle configuré du conteneur NAS.
Aucune lecture documentaire, aucun appel Files upload, aucun repli par clé API.
L'appel exige `--run-real`, consomme les limites du forfait et attend la fin
du flux. Délai 60 secondes, sortie limitée à 2000 caractères, pas de retries.

Le script est transféré hors dépôt dans le dossier privé du propriétaire sur
le NAS ; son exécution Docker nécessite un sudo interactif :

```bash
sudo /usr/local/bin/docker exec -i einstein-core python - --run-real \
  < /var/services/homes/tonio/.einstein-ocr-probe.py
```

Texte de référence présent uniquement dans l'image, pas dans la consigne :

```text
TEST OCR
NAS 192.168.1.3
TOTAL 123.45 CHF
```

Le script affiche la transcription et une comparaison exacte. Un écart de
mise en forme n'est pas nécessairement une erreur de lecture : examiner la
sortie. Même une réussite n'établit pas la qualité sur scans réels, tableaux
ou manuscrits. L’image synthétique a été vérifiée visuellement sur le Mac
puis transcrite sur le NAS ; voir le résultat ci-dessous. Aucun document réel
n’a été envoyé.

[Entrées acceptées par le parcours Plus](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations) : images et fichiers selon le modèle,
sans API d'upload Files. Vérifié le 17 octobre 2026.

## Vision Plus validée — 17 octobre 2026

Sortie transmise par le propriétaire après exécution dans le conteneur NAS :

```text
Fournisseur=chatgpt modèle=gpt-6-luna
TEST OCR
NAS 192.168.1.3
TOTAL 123.45 CHF
Transcription exacte : oui
```

L'image synthétique est transcrite exactement. Cela valide cette entrée image
avec la session et le modèle testés, pas encore l'envoi PDF, les fichiers Word,
les scans complexes ni un traitement de masse. Aucun décompte détaillé de
consommation ou relevé de latence n'a été enregistré.

Orientation retenue selon la préférence du propriétaire : préparer le
traitement OpenAI du corpus sélectionné. L'option OCR local décrite plus haut
reste une alternative ; Tesseract n'est pas installé. L'extraction locale
actuelle reste inchangée et aucun document réel n'est envoyé automatiquement.

Le prochain lot doit ajouter un traitement explicitement déclenché, séparé
du démarrage HTTP, avec un fichier à la fois, un plafond de fichiers/pages,
un cache local lié à l'empreinte et au modèle, des références aux sources et
une reprise des fichiers non terminés. Les fichiers inchangés déjà traités
ne doivent pas être renvoyés à chaque recherche. Aucun repli facturable par
clé API. D'abord vérifier quelques documents choisis avant le lot complet.

## Lot OpenAI et cache — implémentation locale

Une commande séparée transmet les PDF et Word `.docx` inline à Responses,
et les textes/Markdown UTF-8 comme texte. Aucun appel à Files upload. Le modèle
retourne un JSON de transcription, validé avant écriture du cache. La réception
de `response.completed` reste obligatoire, sans repli par clé API. Le test
réel image réussi ne valide pas encore ces entrées PDF/Word : les premiers
fichiers réels restent à contrôler avant d'élargir le lot.

Plafonds initiaux : un MiB par fichier, dix pages par PDF, 65 536 caractères
pour la réponse, un appel par commande par défaut (maximum dix), budget de
parcours 300 secondes. Les PDF chiffrés ou dépassant le plafond sont écartés
avant l'envoi. Le contrôle de pages PDF reste dans l'extracteur isolé. Les
fichiers plus grands ne sont pas découpés automatiquement dans ce lot.

La sortie doit contenir une entrée par page physique PDF ; Word et textes
ont une seule entrée sans numéro de page. Une réponse non JSON, vide, refusée,
interrompue ou avec une pagination incohérente n'est pas mise en cache.
Les contrôles structurels ne garantissent pas l'exactitude de la transcription.

Le cache est privé (répertoire 0700, propriétaire UID du Core ; fichiers 0600),
écrit atomiquement, et contient les textes transmis/reconnus. Sa clé inclut
l'empreinte source, le chemin relatif, le corpus, le modèle demandé et la
version de la consigne. Les fichiers inchangés sont réutilisés ; les échecs
sont repris lors d'une exécution explicite ultérieure. Aucun retry automatique.
Un verrou exclut les ingestions simultanées utilisant ce cache. Éviter les
questions IA pendant un lot : la limite de concurrence HTTP ne couvre pas
ce processus d'ingestion.

Le mode `openai` charge uniquement les transcriptions du cache, sans appel
fournisseur. Fichier modifié, cache absent/invalide ou source supprimée :
aucun ancien texte n'est repris lors de la reconstruction de l'instantané.
L'index mémoire reste figé jusqu'au redémarrage du Core, même après ingestion.
Les anciennes entrées restent sur disque jusqu'à un nettoyage explicite ;
la suppression d'une source n'est donc pas une suppression du cache disque.

### Déploiement à préparer après revue et commit

Sur le NAS, créer le seul dossier cache dédié :

```bash
sudo install -d -o 10001 -g 10001 -m 0700 \
  /volume1/docker/einstein/data/einstein-documents
```

Dans le `.env` runtime :

```dotenv
COMPOSE_FILE=compose.yaml:compose.chatgpt.yaml:compose.documents.yaml:compose.documents-openai.yaml
DOCUMENTS_DIR=/volume1/Documents/03_Tonio/Travail
DOCUMENTS_CACHE_DIR=/volume1/docker/einstein/data/einstein-documents
EINSTEIN_DOCUMENTS_ENABLED=true
```

Conserver les variables Plus existantes. Après mise à jour du clone, build
et déploiement avec les scripts habituels, l'index peut être vide tant que
le corpus n'a pas été traité. Déclencher un premier envoi explicitement :

```bash
sudo /usr/local/bin/docker exec einstein-core \
  python -m einstein_core.documents.ingest --run-real --max-files 1
```

La commande transmet au plus un fichier nécessitant une transcription et
n'affiche que les compteurs, jamais le texte. Le fichier choisi dépend de
l'ordre du parcours ; pour une validation initiale ciblée, préparer un petit
corpus de test choisi avant le corpus complet. Chaque nouvelle exécution
réutilise le cache puis continue dans la limite indiquée. Les compteurs
`partiel` signalent limites ou exclusions, sans promettre une couverture totale.

Pour charger les nouvelles transcriptions dans l'index, redémarrer uniquement
le service Core :

```bash
cd ~/Development/Einstein/compose/einstein-core
sudo /usr/local/bin/docker compose --env-file .env restart api
```

Contrôler ensuite healthy et la recherche depuis le Mac LAN/VPN. Retirer le
complément `compose.documents-openai.yaml` rétablit le mode local après
redéploiement. Le cache contient des données documentaires : le protéger comme
les sources et définir sa rétention/sauvegarde avant l'usage régulier.
Aucune ingestion réelle ni modification de configuration NAS n'a été exécutée
pour cette implémentation ; les tests utilisent un faux fournisseur.

Vérification après ajout du cache : **137 tests réussis**, sans appel réseau
fournisseur, dont validation des requêtes SDK inline dans les quatre formats,
budget d'appels, réutilisation et invalidation du cache, pagination, refus des
sorties invalides, verrou, permissions et recherche cache seule. `compileall`,
`pip check`, MkDocs strict et `git diff --check` passent. Les compléments YAML
sont vérifiés ; la fusion Compose réelle reste à valider sur le NAS.

## Validation NAS du mode local sur corpus synthétique — 17 octobre 2026

Corpus dédié `/volume1/docker/einstein/tmp/documents-test`, dossier
`10001:10001` en 0750, deux fichiers synthétiques en 0640 (`assurance.txt`,
`chaudiere.md`). Aucun document réel n'est monté. Le `.env` runtime a été
sauvegardé dans le dossier personnel privé avant modification :

```dotenv
COMPOSE_FILE=compose.yaml:compose.chatgpt.yaml:compose.documents.yaml
DOCUMENTS_DIR=/volume1/docker/einstein/tmp/documents-test
EINSTEIN_DOCUMENTS_ENABLED=true
```

Déploiement par `stack-up.sh` avec le code applicatif de `f618387` (commit
exact du clone non relevé), image `sha256:d7f10042f93c897362aef96b2dca394c2e741ba4704962a0643721dc0dfdb386`.
La fusion Compose avec Plus est acceptée ; conteneur `healthy` 40 secondes
après création. Mémoire relevée : 80 MiB puis 77 MiB sur 256 MiB.

Recherches HTTPS depuis le Mac sur le LAN, index construit à `10:27:33Z` :

| Requête | Résultat |
|---|---|
| `assurance habitation` | HTTP 200, `indexed_files: 2`, `skipped_files: 0`, `partial: false`, résultat `assurance.txt`, score 2 |
| `piscine` | mêmes compteurs, `results: []` |

Ces essais valident montage en lecture seule, permissions, extraction au
démarrage et accès par le reverse proxy. Ils ne caractérisent ni le temps de
démarrage ni la mémoire sur le corpus réel, et le refus externe de la route
reste à contrôler. Prochaine étape : vérifier taille et droits du dossier
`Travail` pour l'UID 10001 avant de modifier `DOCUMENTS_DIR`.

## Premier dossier réel et indexation en arrière-plan — 17 octobre 2026

Contrôle préalable du dossier `Travail` par un conteneur jetable sans réseau,
UID 10001, lecture seule, compteurs uniquement : 65 507 entrées, 13 219
candidats, 443 fichiers de plus de 5 MiB, profondeur 18, aucun élément
illisible. Le dossier complet dépasse largement les plafonds (1000 entrées,
100 candidats, profondeur 8). Seuls les sous-dossiers `Credit Suisse` (19
candidats) et `Lombard Odier` (57 candidats, à plat) les respectent.

`DOCUMENTS_DIR` pointe désormais vers `Travail/Lombard Odier`. La recherche
« LATAM » depuis le Mac retourne deux sources pertinentes (Word et PDF page 1),
mais avec `indexed_files: 13`, `skipped_files: 7`, `partial: true` : 20 fichiers
traités sur 57. Démarrage du conteneur `10:34:43Z`, index `10:35:19Z` : le
budget de trente secondes est atteint, chaque extraction lançant un
sous-processus Python sur le DS918+.

Correctif local : l'index est construit en arrière-plan avec un budget de
300 secondes (`EINSTEIN_DOCUMENTS_INDEX_BUDGET_SECONDS`, transmis par le
complément Compose). Le Core répond pendant l'extraction ; la recherche
retourne 503 « Indexation documentaire en cours » jusqu'à la fin. Le journal
indique à la fin les compteurs, sans nom ni contenu. L'arrêt du service
interrompt le parcours. 143 tests réussis ; correctif non déployé.
Voir la révision de l'[ADR-0009](../adr/0009-recherche-documentaire-locale.md).

## Indexation en arrière-plan validée et diagnostic des exclusions

Après déploiement de `5f235c7`, la recherche « LATAM » retourne les mêmes
sources pertinentes avec `indexed_files: 30`, `skipped_files: 27`,
`partial: true` (index à `10:43:30Z`) : les 57 candidats sont désormais tous
parcourus.

Diagnostic dans un conteneur jetable (même image et extracteur, UID 10001,
sans réseau, lecture seule, 256 MiB, délai 60 s), compteurs uniquement :

| Cause | Fichiers |
|---|---|
| Extraction réussie en moins de 3 s (médiane 1,7 s, maximum 2,8 s) | 30 |
| PDF sans texte extractible (scans) | 22 |
| Plus de 5 MiB | 5 |

Total extrait : 101 200 caractères, loin du plafond d'un million. Aucune
exclusion n'est due au délai, mais le maximum observé est proche des trois
secondes par fichier sur le DS918+. Les scans représentent 39 % des candidats
de ce dossier : la reconnaissance de texte (OCR local ou vision OpenAI,
décrites plus haut) conditionne leur couverture.

## Refus externe de la route documentaire — 17 octobre 2026

Depuis le Mac relié au partage de connexion 4G de l'iPhone (passerelle par
défaut `172.20.10.1`, interface `en7`, VPN non actif), la requête POST vers
`/api/v1/documents/recherche` reçoit `HTTP/2 403` de nginx
(`Sat, 17 Oct 2026 12:52:27 GMT`), page d'erreur Synology sans contenu
documentaire. L'accès LAN est validé par les recherches précédentes.

Depuis la même connexion 4G avec OpenVPN actif (route vers `192.168.1.3`
par `utun4`), la recherche « LATAM » répond normalement : `indexed_files: 30`,
`skipped_files: 27`, `partial: true`, première source attendue.

## Première évaluation de pertinence

La recherche « banque » retournait cinq passages du même document (quatre de
la version Word, un de la version PDF), alors que d'autres documents du
dossier contiennent ce mot selon le propriétaire : le classement par passage
laissait un long document occuper toute la liste. Correctif local : un seul
résultat par document, son meilleur passage. Les versions Word et PDF d'un
même contenu restent deux documents distincts. 144 tests réussis ; correctif
non déployé. L'évaluation reprend après déploiement.

Après déploiement de `18efbd9`, « banque » retourne cinq documents distincts.
« piscine » ne retourne rien, comme attendu. « secret bancaire » ne retournait
rien malgré un document `Directive_secret_bancaire` : son texte PDF sortait sans
espaces. Diagnostic dans un conteneur jetable, compteurs uniquement :

| Mode pypdf | Durée | Mots | Mots > 25 caractères | « secret » | « bancaire » |
|---|---|---|---|---|---|
| simple | 1,2 s | 517 | 162 | 0 | 0 |
| `layout` | 1,2 s | 2151 | 0 | 40 | 2 |

Correctif local : rattrapage `layout` par page en cas de mots collés et délai
par fichier porté à dix secondes. 145 tests réussis ; correctif non déployé.
Voir la révision de l'[ADR-0009](../adr/0009-recherche-documentaire-locale.md).

## Évaluation de pertinence après correctifs — 17 octobre 2026

Après déploiement de `3dd39d9`, compteurs inchangés (`indexed_files: 30`,
`skipped_files: 27`) : le rattrapage `layout` n'a écarté aucun fichier.

| Recherche | Résultat | Appréciation |
|---|---|---|
| `secret bancaire` | directive (p. 1) et PDF Scanbot du même jour, score 4 | attendu ; le PDF Scanbot avait le même défaut d'espacement |
| `banque` | cinq documents distincts, directive et Scanbot désormais inclus | pertinent |
| `piscine`, `TON_MOT` | aucun résultat | attendu |
| `custody` | aucun résultat | non confirmé par le propriétaire |
| `responsable` | préparation de réunion (Word et PDF) | non confirmé |

Limites observées : les versions Word et PDF d'un même contenu apparaissent
deux fois ; les 22 scans sans texte restent invisibles ; la recherche exige
tous les mots dans un même passage, sans variantes ni pluriels. Un certificat
de salaire figure parmi les résultats : tout appareil du LAN ou du VPN peut en
lire l'extrait, la route n'ayant pas d'authentification.

## OCR local des PDF scannés — implémentation locale

Cadrage validé par le propriétaire dans l'[ADR-0010](../adr/0010-ocr-local-pdf-scannes.md),
avec des plafonds de 50 MiB et 80 pages par fichier. La commande
`python -m einstein_core.documents.ocr` rend chaque page sans texte avec
`pdftoppm` (300 dpi, niveaux de gris) puis la reconnaît avec Tesseract `fra`.
Elle n'affiche que des compteurs, traite un fichier à la fois, 120 s au plus
par page, avec plafonds de fichiers (`--max-files`, 1 à 200) et de durée
(`--max-minutes`, 1 à 600) et reprise à l'exécution suivante.

L'image n'embarque les binaires que si `INSTALL_OCR=true`, fixé par le
complément `compose.documents-ocr.yaml`. Celui-ci monte le cache en lecture
seule pour le Core et définit un service `ocr` à profil, jamais démarré par
`stack-up.sh` : sans réseau, 768 MiB, `cpu_shares` 128, système de fichiers en
lecture seule, `/tmp` de 256 MiB, originaux en lecture seule.

Tests : faux moteur pour reconnaissance, cache privé, reprise, invalidation
après modification ou changement de version, échec sans message, entrée de
cache invalide et recherche marquée `ocr: true` ; un test avec les vrais
binaires sur un PDF composé d'une seule image est sauté s'ils sont absents.
Aucun document réel n'a été traité.

### Déploiement à préparer après revue

Créer le cache privé :

```bash
sudo install -d -o 10001 -g 10001 -m 0700 /volume1/docker/einstein/data/einstein-ocr
```

Dans le `.env` runtime, ajouter le complément et le dossier :

```dotenv
COMPOSE_FILE=compose.yaml:compose.chatgpt.yaml:compose.documents.yaml:compose.documents-ocr.yaml
DOCUMENTS_OCR_CACHE_DIR=/volume1/docker/einstein/data/einstein-ocr
```

Reconstruire et redéployer avec `stack-up.sh`, puis lancer un premier fichier :

```bash
cd ~/Development/Einstein/compose/einstein-core
sudo /usr/local/bin/docker compose --env-file .env run --rm ocr --max-files 1
```

Redémarrer le service Core pour recharger l'index avec le texte reconnu.
Retour arrière : retirer le complément du `COMPOSE_FILE` et redéployer ;
le cache peut être conservé ou supprimé séparément.

### Premier OCR sur le NAS — 17 octobre 2026

Après déploiement de `dd582b5` avec `compose.documents-ocr.yaml` et le cache
`/volume1/docker/einstein/data/einstein-ocr` (`10001:10001`, 0700), la commande
`run --rm ocr --max-files 1` affiche :

```text
reconnus=1 pages_reconnues=1 deja_en_cache=0 sans_besoin=6 ecartes=0 echecs=0 partiel=True
```

Durée totale 1 min 13 s, démarrage du conteneur et lecture de six PDF avec
texte compris. La chaîne `pdftoppm` puis Tesseract `fra` est validée dans
l'image Debian. pypdf a affiché des avertissements de polices (`fontTools`
absent) contenant des dictionnaires de police, sans texte documentaire :
la commande coupe désormais la journalisation, comme l'extracteur.

### Lot OCR complet et recherche — 17 octobre 2026

Après déploiement de `5e018f9`, `run --rm ocr --max-files 30 --max-minutes 120` :

```text
reconnus=25 pages_reconnues=130 deja_en_cache=1 sans_besoin=27 ecartes=0 echecs=0 partiel=False
```

Durée 25 min 19 s, soit environ 11,7 s par page sur le DS918+. Vingt-six
documents ont une entrée OCR : les 22 scans et quatre des cinq fichiers de plus
de 5 MiB. Une relance immédiate retourne `deja_en_cache=26` en 37 s, sans
retraitement.

Après redémarrage du Core, « banque » retourne `indexed_files: 54`,
`skipped_files: 3` (contre 30 et 27), avec en tête quatre documents reconnus
par OCR (contrat de travail, ouverture de compte, résiliation et convention
de résiliation) marqués `ocr: true`.

Les trois fichiers encore écartés seraient des PDF de plus de 5 MiB contenant
déjà du texte : trop grands pour l'extracteur ordinaire, ils ne nécessitent
pas d'OCR et n'ont donc pas d'entrée en cache.

Correctif local : la commande OCR met aussi en cache le texte des PDF que
l'extracteur ordinaire refuse (plus de 5 MiB, 50 pages ou 100 000 caractères)
même sans page à reconnaître ; compteur `texte_seul`. 151 tests réussis.
