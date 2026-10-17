# ADR-0010 — OCR local des PDF scannés

- **Statut :** acceptée, implémentée localement, validation NAS à effectuer
- **Date :** 17 octobre 2026

## Contexte

Le premier sous-dossier réel indexé (`Travail/Lombard Odier`) compte 57
candidats, dont 22 PDF sans texte extractible : des scans (39 %). Ils sont
invisibles pour la recherche locale de l'ADR-0009. La vision OpenAI via Plus
est écartée pour ce besoin : quota sur cinq heures partagé avec Codex,
plafond d'un MiB et dix pages par fichier, et transmission de documents
bancaires hors du NAS.

## Décision

Reconnaître localement le texte des pages sans texte avec Tesseract
(langue `fra`), appelé en ligne de commande, après rendu des pages par
`pdftoppm` (paquet Debian `poppler-utils`) à 300 dpi en niveaux de gris.
Aucune bibliothèque Python n'est ajoutée ; aucun service permanent.

Les binaires sont installés uniquement si l'image est construite avec
l'option `INSTALL_OCR`, sélectionnée par un complément Compose dédié,
sur le modèle de `INSTALL_CHATGPT`. L'image de base reste inchangée.

L'OCR est une commande explicite, exécutée dans un conteneur distinct
(`docker compose run --rm`) : sans réseau, UID 10001, système de fichiers
en lecture seule, originaux montés en lecture seule, limite mémoire propre.
Elle ne partage pas la mémoire du Core et n'est jamais lancée au démarrage
ni par une requête HTTP.

## Limites

- un fichier à la fois, pages traitées séquentiellement ;
- 50 MiB et 80 pages au plus par fichier ;
- 120 secondes au plus par page (rendu et reconnaissance) ;
- plafond de fichiers et de durée par exécution, avec reprise ultérieure ;
- seules les pages sans texte extractible sont reconnues ; les pages mixtes
  (texte et image) ne sont pas couvertes ;
- hors périmètre : images isolées, écriture manuscrite, autres langues.

Un scan de 80 pages peut demander de quinze à quarante minutes sur le
DS918+ ; la durée réelle par page sera mesurée sur le NAS avant le lot complet.

## Cache

Un fichier JSON par document dans un dossier runtime privé distinct des
originaux (répertoire 0700, fichiers 0600, propriétaire UID 10001), écrit
atomiquement. Clé : empreinte SHA-256 du fichier, chemin relatif, langue et
résolution. La version de Tesseract est enregistrée dans l'entrée : le Core
lit le cache sans exécuter Tesseract, et la commande OCR retraite un fichier
dont l'entrée provient d'une autre version. Un fichier modifié est retraité,
un fichier inchangé jamais. Les échecs ne sont pas mis en cache et sont repris lors
d'une exécution ultérieure. Le cache contient du texte documentaire : il est
protégé et sauvegardé comme les sources.

## Recherche

Au démarrage, le Core consulte le cache pour les PDF dont une page au moins
est sans texte, ou que l'extracteur ordinaire refuse (taille, pages), sans
exécuter Tesseract. L'entrée contient toutes les pages : texte extrait pour
les pages qui en ont, texte reconnu pour les autres. Les passages issus de
l'OCR portent `ocr: true` dans les résultats. Un PDF entièrement textuel mais
refusé par l'extracteur ordinaire (plus de 5 MiB, 50 pages ou 100 000
caractères) reçoit aussi une entrée, sans reconnaissance, pour ne pas tomber
entre les deux traitements. Une entrée OCR est limitée à
400 000 caractères ; le plafond total de l'index passe de un à trois millions
de caractères, dans la limite mémoire existante du Core. Un cache absent, invalide ou obsolète est
ignoré : le fichier reste compté comme écarté.

## Conséquences

L'image OCR grossit d'environ 40 Mo. Les binaires `pdftoppm` et `tesseract`
analysent des fichiers non fiables : l'isolation par conteneur, les délais et
les plafonds limitent l'exposition sans la supprimer. La qualité dépend des
scans ; les erreurs de reconnaissance sont possibles et non signalées mot à mot.

## Sources

- [Tesseract — données de langue, dont `fra`](https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html)
- [Paquet Debian `tesseract-ocr-fra`](https://packages.debian.org/bookworm/tesseract-ocr-fra)
- [Paquet Debian `poppler-utils`](https://packages.debian.org/bookworm/poppler-utils)
