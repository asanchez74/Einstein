#!/usr/bin/env bash

set -Eeuo pipefail

source "$(dirname "$0")/lib/stack-common.sh"

init_stack "${1:-}"

DATA_DIR="$(
    awk -F= '
        $1 == "DATA_DIR" {
            value = substr($0, index($0, "=") + 1)
            gsub(/^["'\'' ]+|["'\'' ]+$/, "", value)
            print value
            exit
        }
    ' "$ENV_FILE"
)"

[[ -n "$DATA_DIR" ]] ||
    die "variable DATA_DIR absente de ${ENV_FILE}"

[[ "$DATA_DIR" = /* ]] ||
    die "DATA_DIR doit être un chemin absolu"

[[ -d "$DATA_DIR" ]] ||
    die "répertoire de données absent : ${DATA_DIR}"

BACKUP_ROOT="/volume1/docker/einstein/backups/${SERVICE}"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
ARCHIVE="${BACKUP_ROOT}/${SERVICE}-${TIMESTAMP}.tar.gz"
MANIFEST="${ARCHIVE}.txt"

mkdir -p "$BACKUP_ROOT"

WAS_RUNNING=false

restart_stack() {
    if [[ "$WAS_RUNNING" == true ]]; then
        printf '\n=== REDEMARRAGE APRES SAUVEGARDE ===\n'
        compose start
    fi
}

trap restart_stack EXIT

if [[ -n "$(compose ps -q)" ]]; then
    WAS_RUNNING=true

    printf '\n=== ARRET TEMPORAIRE ===\n'
    compose stop
fi

printf '\n=== SAUVEGARDE ===\n'
tar \
    -C "$(dirname "$DATA_DIR")" \
    -czf "$ARCHIVE" \
    "$(basename "$DATA_DIR")"

CHECKSUM="$(sha256sum "$ARCHIVE" | awk '{print $1}')"

{
    printf 'Service=%s\n' "$SERVICE"
    printf 'Date=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')"
    printf 'Hote=%s\n' "$(hostname)"
    printf 'Depot=%s\n' "$REPO_ROOT"
    printf 'Commit=%s\n' "$(git -C "$REPO_ROOT" rev-parse HEAD)"
    printf 'Source=%s\n' "$DATA_DIR"
    printf 'Archive=%s\n' "$ARCHIVE"
    printf 'SHA256=%s\n' "$CHECKSUM"
} > "$MANIFEST"

printf 'Archive : %s\n' "$ARCHIVE"
printf 'SHA256  : %s\n' "$CHECKSUM"
