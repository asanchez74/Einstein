#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

die() {
    printf 'Erreur : %s\n' "$*" >&2
    exit 1
}

init_stack() {
    SERVICE="${1:-}"

    [[ -n "$SERVICE" ]] ||
        die "nom du service manquant"

    STACK_DIR="${REPO_ROOT}/compose/${SERVICE}"
    COMPOSE_FILE="${STACK_DIR}/compose.yaml"
    ENV_FILE="${STACK_DIR}/.env"

    [[ -d "$STACK_DIR" ]] ||
        die "service inconnu : ${SERVICE}"

    [[ -f "$COMPOSE_FILE" ]] ||
        die "fichier absent : ${COMPOSE_FILE}"

    [[ -f "$ENV_FILE" ]] ||
        die "fichier local absent : ${ENV_FILE}"

    if docker info >/dev/null 2>&1; then
        DOCKER=(docker)
    elif sudo -v && sudo docker info >/dev/null 2>&1; then
        DOCKER=(sudo docker)
    else
        die "impossible d’accéder au moteur Docker"
    fi
}

compose() {
    (
        cd "$STACK_DIR"
        "${DOCKER[@]}" compose \
            --env-file "$ENV_FILE" \
            "$@"
    )
}
