#!/bin/sh
# Surveillance de la saturation du NAS (incident du 4 novembre 2026).
# Lancé par une tâche DSM en root ; un code de sortie non nul déclenche
# l'envoi des détails par courriel. Une ligne d'état est toujours affichée.

set -eu

PROC_STAT="${PROC_STAT:-/proc/stat}"
PROC_MEMINFO="${PROC_MEMINFO:-/proc/meminfo}"
PROC_MDSTAT="${PROC_MDSTAT:-/proc/mdstat}"
PROC_LOADAVG="${PROC_LOADAVG:-/proc/loadavg}"
STATE_FILE="${STATE_FILE:-/volume1/docker/einstein/tmp/nas-health-check.state}"

# Conteneur interrogé par « docker exec » ; ignoré s'il n'est pas démarré
# (arrêt volontaire, sauvegarde en cours).
DOCKER_PROBE="${DOCKER_PROBE:-pihole}"
DOCKER_TIMEOUT="${DOCKER_TIMEOUT:-10}"
# Attente disque : pourcentage sur l'échantillon, et nombre d'exécutions
# consécutives au-dessus du seuil avant l'alerte (pics des sauvegardes).
SAMPLE_SECONDS="${SAMPLE_SECONDS:-10}"
IOWAIT_MAX="${IOWAIT_MAX:-40}"
IOWAIT_RUNS="${IOWAIT_RUNS:-2}"
SWAP_USED_MAX_MB="${SWAP_USED_MAX_MB:-2048}"
MEM_AVAILABLE_MIN_MB="${MEM_AVAILABLE_MIN_MB:-500}"

if [ "$(id -u)" -ne 0 ]; then
    echo "ERREUR: ce script doit être exécuté avec sudo/root." >&2
    exit 1
fi

for file in "$PROC_STAT" "$PROC_MEMINFO" "$PROC_MDSTAT" "$PROC_LOADAVG"; do
    if [ ! -r "$file" ]; then
        echo "ERREUR: fichier illisible: $file" >&2
        exit 1
    fi
done

ALERTS=0

alert() {
    echo "ALERTE: $*" >&2
    ALERTS=$((ALERTS + 1))
}

# Somme des compteurs CPU et compteur iowait (5e valeur) de la ligne « cpu ».
cpu_counters() {
    awk '$1 == "cpu" { t = 0; for (i = 2; i <= NF; i++) t += $i; print t, $6; exit }' "$PROC_STAT"
}

meminfo_kb() {
    awk -v key="$1:" '$1 == key { print $2; exit }' "$PROC_MEMINFO"
}

# 1. Docker répond-il ?
if command -v docker >/dev/null 2>&1; then
    running=$(timeout "$DOCKER_TIMEOUT" docker inspect -f '{{.State.Running}}' "$DOCKER_PROBE" 2>/dev/null) || running=""
    if [ "$running" = "true" ]; then
        rc=0
        timeout "$DOCKER_TIMEOUT" docker exec "$DOCKER_PROBE" true >/dev/null 2>&1 || rc=$?
        if [ "$rc" -eq 0 ]; then
            DOCKER_STATE="ok"
        elif [ "$rc" -eq 124 ]; then
            DOCKER_STATE="bloqué"
            alert "docker exec $DOCKER_PROBE ne répond pas en ${DOCKER_TIMEOUT} s (démon Docker bloqué ?)"
        else
            DOCKER_STATE="erreur $rc"
            alert "docker exec $DOCKER_PROBE a échoué (code $rc)"
        fi
    elif [ -z "$running" ]; then
        # inspect lui-même bloqué ou conteneur absent
        rc=0
        timeout "$DOCKER_TIMEOUT" docker version >/dev/null 2>&1 || rc=$?
        if [ "$rc" -eq 124 ]; then
            DOCKER_STATE="bloqué"
            alert "le démon Docker ne répond pas en ${DOCKER_TIMEOUT} s"
        else
            DOCKER_STATE="$DOCKER_PROBE absent"
        fi
    else
        DOCKER_STATE="$DOCKER_PROBE arrêté"
    fi
else
    DOCKER_STATE="introuvable"
    alert "commande docker introuvable (PATH=$PATH)"
fi

# 2. Attente disque sur l'échantillon.
set -- $(cpu_counters)
total1=$1 iowait1=$2
sleep "$SAMPLE_SECONDS"
set -- $(cpu_counters)
total2=$1 iowait2=$2
delta=$((total2 - total1))
if [ "$delta" -gt 0 ]; then
    IOWAIT=$(( (iowait2 - iowait1) * 100 / delta ))
else
    IOWAIT=0
fi

previous=0
if [ -r "$STATE_FILE" ]; then
    previous=$(awk -F= '$1 == "iowait_high_runs" { print $2 + 0 }' "$STATE_FILE")
    previous=${previous:-0}
fi
if [ "$IOWAIT" -ge "$IOWAIT_MAX" ]; then
    high_runs=$((previous + 1))
else
    high_runs=0
fi
if [ "$high_runs" -ge "$IOWAIT_RUNS" ]; then
    alert "attente disque ${IOWAIT} % (seuil ${IOWAIT_MAX} %) depuis ${high_runs} exécutions"
fi
if ! printf 'iowait_high_runs=%s\n' "$high_runs" > "$STATE_FILE" 2>/dev/null; then
    echo "AVERTISSEMENT: état non enregistré dans $STATE_FILE" >&2
fi

# 3. et 4. Mémoire et swap.
swap_total=$(meminfo_kb SwapTotal)
swap_free=$(meminfo_kb SwapFree)
mem_available=$(meminfo_kb MemAvailable)
SWAP_USED_MB=$(( (${swap_total:-0} - ${swap_free:-0}) / 1024 ))
MEM_AVAILABLE_MB=$(( ${mem_available:-0} / 1024 ))
if [ "$SWAP_USED_MB" -ge "$SWAP_USED_MAX_MB" ]; then
    alert "swap occupé ${SWAP_USED_MB} Mo (seuil ${SWAP_USED_MAX_MB} Mo)"
fi
if [ "$MEM_AVAILABLE_MB" -lt "$MEM_AVAILABLE_MIN_MB" ]; then
    alert "mémoire disponible ${MEM_AVAILABLE_MB} Mo (seuil ${MEM_AVAILABLE_MIN_MB} Mo)"
fi

# 5. RAID : un « _ » dans [UU...] signale un disque manquant.
DEGRADED=$(awk '
    /^md[0-9]+ :/ { name = $1 }
    /\[[U_]+\]/ && name != "" {
        if (match($0, /\[[U_]+\]/)) {
            status = substr($0, RSTART, RLENGTH)
            if (index(status, "_")) { printf "%s%s %s", sep, name, status; sep = ", " }
        }
        name = ""
    }' "$PROC_MDSTAT")
if [ -n "$DEGRADED" ]; then
    alert "RAID dégradé : $DEGRADED"
    RAID_STATE="dégradé"
else
    RAID_STATE="ok"
fi

LOAD=$(awk '{ print $1, $2, $3 }' "$PROC_LOADAVG")
echo "charge ${LOAD} ; attente disque ${IOWAIT} % ; swap ${SWAP_USED_MB} Mo ; mémoire disponible ${MEM_AVAILABLE_MB} Mo ; RAID ${RAID_STATE} ; docker ${DOCKER_STATE}"

if [ "$ALERTS" -gt 0 ]; then
    echo "ERREUR: ${ALERTS} alerte(s). Procédure : docs/docker-operations.md, section « Surveillance de la saturation »." >&2
    exit 1
fi
