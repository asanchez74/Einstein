# ADR-0009 — Recherche documentaire locale

- **Statut :** implémentée localement, validation NAS à effectuer
- **Date :** 17 octobre 2026

## Besoin et décision

Le propriétaire choisit les PDF, Word et textes du dossier `/volume1/Documents/03_Tonio/Travail`.
Ajouter un module Documents au monolithe : extraction locale puis recherche
lexicale dans un instantané en mémoire. Aucun besoin démontré de base vectorielle,
d'embeddings ou de nouveau service. Les documents ne sont pas transmis à l'IA.

Le dossier monté en lecture seule constitue le périmètre autorisé, y compris
ses sous-dossiers visibles. Il n'existe pas d'autorisation par utilisateur :
tout client autorisé à consulter cette API peut obtenir les extraits du corpus.
L'accès reste limité par le reverse proxy LAN/VPN existant.

`pypdf==6.21.0` extrait les pages PDF. Le XML du corps des `.docx` est lu avec
la bibliothèque standard, sans exécuter de macro ou récupérer de lien distant.
Les `.txt` et `.md` doivent être UTF-8. Les anciens `.doc` ne sont pas pris en charge.

## Limites et isolation

Extraction séquentielle dans des sous-processus, trois secondes par fichier,
budget de parcours configurable (`EINSTEIN_DOCUMENTS_INDEX_BUDGET_SECONDS`,
300 secondes par défaut, initialement trente). Sous Linux, chaque extracteur a une limite
d'espace virtuel de 128 MiB ; elle ne remplace pas la limite mémoire Docker
partagée avec le Core. Sur macOS, le délai s'applique sans ce plafond virtuel.
Les erreurs de parseur et les contenus ne sont pas journalisés.

Limites : 100 fichiers candidats traités, 1000 entrées de répertoire parcourues,
profondeur huit, 5 MiB par fichier, 50 pages par PDF, XML Word décompressé de
2 MiB, 100 000 caractères extraits par fichier et un million de caractères de
passages au total. Les erreurs et plafonds rendent le résultat partiel explicite.
L'ordre du parcours dépend du système de fichiers ; ce premier lot ne garantit
pas quels fichiers sont retenus si les limites sont atteintes.

Les liens symboliques sont refusés, y compris dans le chemin racine ; les
fichiers sont ouverts relativement aux descripteurs de répertoire et vérifiés
comme réguliers. Les noms commençant par un point sont ignorés. Les liens
physiques ne sont pas distingués des fichiers ordinaires ; préparer un dossier
sélectionné sans lien physique vers un contenu à exclure.

## Conséquences

L'instantané est reconstruit au démarrage et ne suit pas les changements en
cours d'exécution. Une suppression source nécessite un redémarrage pour retirer
ses extraits de la mémoire. Dossier absent : recherche 503, Core préservé.
L'instantané est construit en arrière-plan : le Core, la santé et les
questions répondent pendant l'extraction ; la recherche retourne 503
« indexation en cours » jusqu'à la fin du parcours. L'arrêt du service
interrompt le parcours au fichier suivant.
Aucun fichier d'index persistant ni téléchargement de document n'est ajouté.

Recherche par mots, sans casse ni accents ; tous les mots doivent apparaître
dans un même passage. Pas de synonymes, raisonnement ou garantie de pertinence.
Les références sont relatives au dossier choisi ; PDF : page physique, autres
formats : numéro de passage, sans pagination Word inventée.

PDF chiffrés, scans sans texte et fichiers illisibles sont écartés dans ce lot.
L’OCR local des PDF scannés en français est accepté comme lot suivant, séparé
du démarrage et des requêtes HTTP ; il reste à implémenter. Voir le Sprint 6.
Les en-têtes, notes et zones de texte Word ne sont pas couverts par ce lecteur
minimal. L'interface utilisateur et les réponses IA documentaires sont différées.

## Évolution après essai vision

Le 17 octobre 2026, une image synthétique a été transcrite exactement via Plus
et `gpt-6-luna`. Le propriétaire privilégie désormais un traitement OpenAI du
corpus choisi. Cette évolution est prévue dans le lot suivant, avec traitement
séparé, cache et limites ; elle ne change pas le fonctionnement local décrit
ici. Le test image ne valide pas encore les entrées PDF/Word ni le corpus réel.
Voir le suivi du Sprint 6 pour les preuves et les prochaines étapes.

## Source

[Extraction et limites PDF — documentation pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)

## Complément — traitement OpenAI explicite et cache

Le lot suivant est implémenté localement : un mode `openai` complète le mode
`local` sans le remplacer. La commande d'ingestion envoie les fichiers du
corpus configuré à Plus dans un lot borné. Le cache de transcription est
local, privé et distinct des originaux ; aucune nouvelle infrastructure.
Les recherches n'envoient jamais les documents et restent possibles sans IA
active si un modèle correspondant au cache est configuré.

Le PDF est envoyé entier, sous les plafonds d'un MiB et dix pages. La sortie
est validée structurellement ; les références de pages sont celles produites
par le modèle et leur contenu doit être contrôlé sur des cas réels. Word et
texte n'ont pas de pagination inventée. Les originaux restent en lecture seule.

L'index cache est reconstruit au démarrage après comparaison des empreintes
avec les sources. Une modification/suppression prend effet dans la recherche
au redémarrage ; les anciennes transcriptions sur disque ne sont pas purgées
automatiquement. Le cache inscriptible est limité au dossier dédié ; le reste
du système de fichiers reste en lecture seule. La validation NAS et les
premiers essais PDF/Word restent ouverts.

## Révision : indexation en arrière-plan — 17 octobre 2026

Sur le NAS, le premier dossier réel (57 candidats) n'a été traité qu'à
20 fichiers : le démarrage d'un sous-processus Python par fichier sur le
DS918+ consomme l'essentiel du budget de trente secondes, mesuré à 36 secondes
entre démarrage du conteneur et fin d'indexation. Plutôt que d'allonger le
démarrage bloquant, le parcours est déplacé en tâche de fond avec un budget
de 300 secondes. L'isolation par sous-processus et les autres plafonds sont
conservés. Le dossier `Travail` complet (13 219 candidats, profondeur 18)
reste hors de portée de cette conception : un index persistant et incrémental
ferait l'objet d'une décision distincte, si le besoin est confirmé.
