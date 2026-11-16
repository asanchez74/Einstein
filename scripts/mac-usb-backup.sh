#!/bin/sh
# Copie débranchée (règle 3-2-1, ADR-0014) : recopie depuis le Mac le dépôt
# Hyper Backup du NAS hébergé par le DS212j (chiffré, versionné, même
# périmètre que Swiss Backup) et les sauvegardes UpdraftPlus sur le disque
# externe. Restauration : Hyper Backup Explorer sur le Mac.
#
# Usage : scripts/mac-usb-backup.sh [--dry-run]

set -eu

SOURCE_URL="${SOURCE_URL:-smb://tonio@192.168.1.4/SauvegardeDS918}"
SOURCE_ROOT="${SOURCE_ROOT:-/Volumes/SauvegardeDS918}"
DEST_ROOT="${DEST_ROOT:-/Volumes/Einstein-USB}"
DEST_DIR="${DEST_DIR:-DS212j}"
ITEMS="${ITEMS:-DS918.hbk lisbonne2027}"
# Sauvegarde nocturne du NAS vers le DS212j : 04:15 (ADR-0014).
BUSY_HOUR="${BUSY_HOUR:-04}"
# Dépôt modifié depuis moins de N minutes : sauvegarde probablement en cours.
QUIET_MINUTES="${QUIET_MINUTES:-30}"
# Laisse le temps de saisir le mot de passe au premier montage.
MOUNT_WAIT="${MOUNT_WAIT:-60}"

DRY_RUN=
case "${1:-}" in
    "") ;;
    --dry-run) DRY_RUN=--dry-run ;;
    *) echo "Usage : $0 [--dry-run]" >&2; exit 2 ;;
esac

die() {
    echo "ERREUR: $*" >&2
    exit 1
}

mount_point_of() {
    df -P "$1" 2>/dev/null | awk 'NR == 2 { print $NF }'
}

# 1. Destination : un volume monté, jamais un dossier du disque du Mac.
[ -d "$DEST_ROOT" ] || die "disque externe absent : $DEST_ROOT (brancher le disque)"
[ "$(mount_point_of "$DEST_ROOT")" = "$DEST_ROOT" ] ||
    die "$DEST_ROOT n'est pas un volume monté : refus d'écrire"

# 2. Source : partage du DS212j, monté au besoin.
if [ ! -d "$SOURCE_ROOT/DS918.hbk" ]; then
    echo "Montage de ${SOURCE_URL}…"
    open "$SOURCE_URL" || true
    i=0
    while [ ! -d "$SOURCE_ROOT/DS918.hbk" ] && [ "$i" -lt "$MOUNT_WAIT" ]; do
        sleep 1
        i=$((i + 1))
    done
fi
[ -r "$SOURCE_ROOT/DS918.hbk/_Syno_TaskConfig" ] ||
    die "dépôt Hyper Backup introuvable : $SOURCE_ROOT/DS918.hbk"

# 3. Pas pendant la sauvegarde du NAS vers le DS212j.
[ "$(date +%H)" != "$BUSY_HOUR" ] ||
    die "sauvegarde nocturne du DS212j en cours (${BUSY_HOUR}h) : relancer plus tard"
recent=$(find "$SOURCE_ROOT/DS918.hbk" -maxdepth 2 -mmin "-${QUIET_MINUTES}" 2>/dev/null | head -1)
[ -z "$recent" ] ||
    die "dépôt modifié depuis moins de ${QUIET_MINUTES} min ($recent) : sauvegarde en cours ?"

for item in $ITEMS; do
    [ -d "$SOURCE_ROOT/$item" ] || die "source absente : $SOURCE_ROOT/$item"
done

# 4. Copie miroir, limitée à chaque dossier copié.
mkdir -p "$DEST_ROOT/$DEST_DIR"
start=$(date '+%Y-%m-%d %H:%M:%S')
copy_start=$(date +%s)
status=0
for item in $ITEMS; do
    echo "=== $item"
    rsync -rlt --delete $DRY_RUN "$SOURCE_ROOT/$item/" "$DEST_ROOT/$DEST_DIR/$item/" || status=$?
done

# 5. Un dépôt modifié pendant la copie donne une copie incohérente.
elapsed=$((($(date +%s) - copy_start) / 60 + 1))
changed=$(find "$SOURCE_ROOT/DS918.hbk" -maxdepth 2 -mmin "-${elapsed}" 2>/dev/null | head -1)
[ -z "$changed" ] ||
    die "dépôt modifié pendant la copie ($changed) : copie incohérente, relancer le script hors de la sauvegarde nocturne"
[ "$status" -eq 0 ] || die "rsync a échoué (code $status) : relancer le script"

if [ -z "$DRY_RUN" ]; then
    {
        printf 'Debut=%s\n' "$start"
        printf 'Fin=%s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
        printf 'Source=%s\n' "$SOURCE_URL"
        printf 'Elements=%s\n' "$ITEMS"
    } > "$DEST_ROOT/$DEST_DIR/DERNIERE-COPIE.txt"
fi

du -sh "$DEST_ROOT/$DEST_DIR"/* 2>/dev/null || true
echo "Terminé${DRY_RUN:+ (simulation)}. Éjecter le disque avant de le débrancher."
