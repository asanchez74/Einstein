#!/usr/bin/env bash

set -Eeuo pipefail

source "$(dirname "$0")/lib/stack-common.sh"

init_stack "${1:-}"

printf '\n=== ARRET ===\n'
compose down

printf '\nLes volumes persistants n’ont pas été supprimés.\n'
