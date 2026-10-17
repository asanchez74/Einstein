#!/bin/sh
# Exception de routage DSM : réponses de l'adresse LAN NAS vers OpenVPN.
set -eu

ACTION="${1:---check}"
case "$ACTION" in
    --check|--apply|--remove) ;;
    *) echo "Usage: $0 [--check|--apply|--remove]" >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || exit 2
command -v ip >/dev/null 2>&1 || { echo "Commande ip absente" >&2; exit 1; }

if [ "$ACTION" != --check ] && [ "$(id -u)" != 0 ]; then
    echo "Cette opération nécessite root." >&2
    exit 1
fi

RULES=$(ip -4 rule show)
CURRENT=$(printf '%s\n' "$RULES" | awk '$1 == "1:" {
    $1=""; sub(/^[[:space:]]+/, ""); gsub(/[[:space:]]+/, " "); print
}')
PRESENT=false
case "$CURRENT" in
    "") ;;
    "from 192.168.1.3 to 10.8.0.0/24 lookup main"|\
    "from 192.168.1.3/32 to 10.8.0.0/24 lookup main") PRESENT=true ;;
    *) echo "Conflit à la priorité 1 : aucune modification." >&2; exit 1 ;;
esac

case "$ACTION" in
    --check)
        if [ "$PRESENT" = true ]; then
            echo "Exception de retour VPN présente."
            exit 0
        fi
        echo "Exception de retour VPN absente."
        exit 1
        ;;
    --remove)
        if [ "$PRESENT" = true ]; then
            ip -4 rule del priority 1 from 192.168.1.3/32 to 10.8.0.0/24 lookup main
            echo "Exception de retour VPN retirée."
        else
            echo "Exception déjà absente."
        fi
        exit 0
        ;;
esac

if [ "$PRESENT" = true ]; then
    echo "Exception déjà présente : aucune modification."
    exit 0
fi

# Au démarrage, OpenVPN peut ne pas être prêt. Réessayer à la prochaine tâche.
ROUTES=$(ip -4 route show table main)
if ! printf '%s\n' "$ROUTES" | awk '
    $1 == "10.8.0.0/24" {
        for (i=2; i<NF; i++) if ($i == "dev" && $(i+1) == "tun0") found=1
    }
    END {exit !found}
'; then
    echo "Route VPN via tun0 absente : application différée, aucune modification."
    exit 0
fi

ip -4 rule add priority 1 from 192.168.1.3/32 to 10.8.0.0/24 lookup main
echo "Exception de retour VPN ajoutée."
