#!/bin/sh

set -eu

LEASE_FILE="${LEASE_FILE:-/etc/dhcpd/dhcpd.conf.leases}"
DOMAIN="${DOMAIN:-chantevigne.com}"
# Conteneurs Pi-hole à alimenter ; le fichier est écrit dans le volume monté
# sur /etc/pihole de chacun (aucun accès réseau, donc pas de limite macvlan).
PIHOLE_TARGETS="${PIHOLE_TARGETS:-pihole pihole2}"
# Délai maximal (s) de chaque appel docker : un client bloqué empêcherait
# toutes les exécutions suivantes de la tâche planifiée.
DOCKER_TIMEOUT="${DOCKER_TIMEOUT:-30}"

if [ "$(id -u)" -ne 0 ]; then
    echo "ERREUR: ce script doit être exécuté avec sudo/root." >&2
    exit 1
fi

if [ ! -r "$LEASE_FILE" ]; then
    echo "ERREUR: fichier de baux inaccessible: $LEASE_FILE" >&2
    exit 1
fi

TMP=$(mktemp)
TARGET_TMP=

cleanup() {
    rm -f "$TMP" ${TARGET_TMP:+"$TARGET_TMP"}
}

trap cleanup EXIT HUP INT TERM

NOW=$(date +%s)

awk -v now="$NOW" -v domain="$DOMAIN" '
NF >= 4 &&
$3 ~ /^192\.168\.1\.[0-9]+$/ &&
$4 != "*" &&
($1 == 0 || $1 > now) {

    ip = $3
    host = $4
    expiry = $1 + 0

    sub(/\.$/, "", host)

    if (!(ip in best_expiry) || expiry > best_expiry[ip]) {
        best_expiry[ip] = expiry
        hostname[ip] = host
    }
}

END {
    for (ip in hostname) {
        print ip, hostname[ip] "." domain
    }
}
' "$LEASE_FILE" | sort -V > "$TMP"

if [ ! -s "$TMP" ]; then
    echo "ERREUR: aucun bail DHCP exploitable trouvé; fichiers existants conservés." >&2
    exit 1
fi

COUNT=$(wc -l < "$TMP" | tr -d ' ')

# Écrit la liste dans le volume d'un conteneur puis recharge FTL.
# Retourne 1 en cas d'échec, sans interrompre les autres cibles.
sync_target() {
    container="$1"

    data_dir=$(timeout "$DOCKER_TIMEOUT" docker inspect --format \
        '{{range .Mounts}}{{if eq .Destination "/etc/pihole"}}{{.Source}}{{end}}{{end}}' \
        "$container" 2>/dev/null) || {
        echo "ERREUR: $container : conteneur introuvable." >&2
        return 1
    }

    if [ -z "$data_dir" ] || [ ! -d "$data_dir" ]; then
        echo "ERREUR: $container : volume /etc/pihole introuvable." >&2
        return 1
    fi

    output_file="$data_dir/synology-hosts.list"

    if [ -f "$output_file" ] &&
       cmp "$TMP" "$output_file" >/dev/null 2>&1; then
        echo "$container : aucun changement ($COUNT hôtes)."
        return 0
    fi

    TARGET_TMP="${output_file}.tmp.$$"

    if ! cp "$TMP" "$TARGET_TMP" ||
       ! chmod 0644 "$TARGET_TMP" ||
       ! mv -f "$TARGET_TMP" "$output_file"; then
        rm -f "$TARGET_TMP"
        TARGET_TMP=
        echo "ERREUR: $container : écriture impossible de $output_file." >&2
        return 1
    fi

    TARGET_TMP=
    echo "$container : synchronisation effectuée, $COUNT hôtes -> $output_file"

    if ! timeout "$DOCKER_TIMEOUT" docker exec "$container" sh -c '
        PID="$(cat /run/pihole-FTL.pid)"

        # Recharge addn-hosts et vide le cache DNS.
        kill -HUP "$PID"
        sleep 1

        # Force FTL à re-résoudre immédiatement les noms des clients.
        RTMIN="$(pihole-FTL sigrtmin)"
        kill -$((RTMIN + 4)) "$PID"
    '; then
        echo "ERREUR: $container : fichier écrit mais rechargement FTL impossible (conteneur arrêté ou délai de ${DOCKER_TIMEOUT} s dépassé)." >&2
        return 1
    fi

    echo "$container : Pi-hole FTL rechargé et noms clients rafraîchis."
}

FAILED=

for container in $PIHOLE_TARGETS; do
    sync_target "$container" || FAILED="${FAILED:+$FAILED }$container"
done

if [ -n "$FAILED" ]; then
    echo "ERREUR: synchronisation DHCP vers Pi-hole en échec pour : $FAILED" >&2
    exit 1
fi
