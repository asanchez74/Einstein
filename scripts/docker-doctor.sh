#!/usr/bin/env bash

set -Eeuo pipefail

section() {
    printf '\n=== %s ===\n' "$1"
}

if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
    DOCKER_MODE="accès direct"
elif sudo -v && sudo docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
    DOCKER_MODE="sudo"
else
    printf 'Erreur : impossible d’accéder au moteur Docker.\n' >&2
    exit 1
fi

section "HOTE"
printf 'Nom : %s\n' "$(hostname)"
printf 'Date : %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')"
printf 'Utilisateur : %s\n' "$(id)"
printf 'Mode Docker : %s\n' "$DOCKER_MODE"

section "SYSTEME"
if [[ -r /etc.defaults/VERSION ]]; then
    cat /etc.defaults/VERSION
else
    uname -a
fi

section "SOCKET DOCKER"
ls -l /var/run/docker.sock

section "VERSIONS"
"${DOCKER[@]}" version
"${DOCKER[@]}" compose version

section "CONFIGURATION DOCKER"
"${DOCKER[@]}" info --format \
'Nom={{.Name}}
DockerRoot={{.DockerRootDir}}
CPUs={{.NCPU}}
Memoire={{.MemTotal}}
DriverStockage={{.Driver}}
DriverLogs={{.LoggingDriver}}
DriverCgroup={{.CgroupDriver}}
VersionCgroup={{.CgroupVersion}}'

section "CONTENEURS ACTIFS"
"${DOCKER[@]}" ps --format \
'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

section "TOUS LES CONTENEURS"
"${DOCKER[@]}" ps -a --format \
'table {{.Names}}\t{{.Image}}\t{{.Status}}'

section "UTILISATION DOCKER"
"${DOCKER[@]}" system df

section "STOCKAGE"
df -h /volume1

section "ARBORESCENCE EINSTEIN"
if [[ -d /volume1/docker/einstein ]]; then
    find /volume1/docker/einstein \
        -maxdepth 2 \
        -printf '%M %u:%g %p\n' \
        | sort
else
    printf '/volume1/docker/einstein absent\n'
fi

section "DEPOT"
REPOSITORY="${HOME}/Development/Einstein"

if [[ -d "${REPOSITORY}/.git" ]]; then
    git -C "$REPOSITORY" status --short --branch
    git -C "$REPOSITORY" remote -v
else
    printf 'Dépôt absent : %s\n' "$REPOSITORY"
fi

section "RESULTAT"
printf 'Diagnostic terminé sans modification du système.\n'
