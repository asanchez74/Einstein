#!/usr/bin/env bash

set -Eeuo pipefail

source "$(dirname "$0")/lib/stack-common.sh"

SERVICE="${1:-}"
[[ $# -gt 0 ]] && shift

init_stack "$SERVICE"

if [[ $# -gt 0 ]]; then
    compose logs "$@"
else
    compose logs --tail 200 --follow
fi
