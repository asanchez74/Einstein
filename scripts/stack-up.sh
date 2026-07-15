#!/usr/bin/env bash

set -Eeuo pipefail

source "$(dirname "$0")/lib/stack-common.sh"

init_stack "${1:-}"

printf '\n=== VALIDATION ===\n'
compose config >/dev/null

printf '\n=== IMAGES ===\n'
compose pull

printf '\n=== DEMARRAGE ===\n'
compose up -d --remove-orphans

printf '\n=== ETAT ===\n'
compose ps
