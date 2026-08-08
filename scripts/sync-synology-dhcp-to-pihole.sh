#!/bin/sh

set -eu

LEASE_FILE="${LEASE_FILE:-/etc/dhcpd/dhcpd.conf.leases}"
OUTPUT_FILE="${OUTPUT_FILE:-/volume1/docker/einstein/data/pihole/synology-hosts.list}"
DOMAIN="${DOMAIN:-chantevigne.com}"
CONTAINER="${CONTAINER:-pihole}"

if [ "$(id -u)" -ne 0 ]; then
    echo "ERREUR: ce script doit être exécuté avec sudo/root." >&2
    exit 1
fi

if [ ! -r "$LEASE_FILE" ]; then
    echo "ERREUR: fichier de baux inaccessible: $LEASE_FILE" >&2
    exit 1
fi

OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
mkdir -p "$OUTPUT_DIR"

TMP="${OUTPUT_FILE}.tmp.$$"

cleanup() {
    rm -f "$TMP"
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
    echo "ERREUR: aucun bail DHCP exploitable trouvé; fichier existant conservé." >&2
    exit 1
fi

COUNT=$(wc -l < "$TMP" | tr -d ' ')

if [ -f "$OUTPUT_FILE" ] &&
   cmp "$TMP" "$OUTPUT_FILE" >/dev/null 2>&1; then
    echo "Aucun changement ($COUNT hôtes)."
    exit 0
fi

chmod 0644 "$TMP"
mv -f "$TMP" "$OUTPUT_FILE"
trap - EXIT HUP INT TERM

echo "Synchronisation effectuée: $COUNT hôtes -> $OUTPUT_FILE"

if docker inspect "$CONTAINER" >/dev/null 2>&1; then
    docker exec "$CONTAINER" sh -c '
        PID="$(cat /run/pihole-FTL.pid)"

        # Recharge addn-hosts et vide le cache DNS.
        kill -HUP "$PID"
        sleep 1

        # Force FTL à re-résoudre immédiatement les noms des clients.
        RTMIN="$(pihole-FTL sigrtmin)"
        kill -$((RTMIN + 4)) "$PID"
    '

    echo "Pi-hole FTL rechargé et noms clients rafraîchis."
fi
