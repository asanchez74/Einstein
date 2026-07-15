#!/usr/bin/env bash

set -Eeuo pipefail

source "$(dirname "$0")/lib/stack-common.sh"

init_stack "${1:-}"

printf '\n=== ETAT ===\n'
compose ps

printf '\n=== PROCESSUS ===\n'
compose top
