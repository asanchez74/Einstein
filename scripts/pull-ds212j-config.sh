#!/bin/sh
# Copie la configuration domotique du DS212j (eibd, linknx, application eib)
# vers le DS918+, où instantanés, Swiss Backup et Glacier la protègent.
# Ne supprime rien : ajoute et met à jour seulement (pas de --delete).
set -eu

SOURCE_HOST="${SOURCE_HOST:-192.168.1.4}"
SOURCE_PORT="${SOURCE_PORT:-22606}"
SOURCE_USER="${SOURCE_USER:-tonio}"
SSH_KEY="${SSH_KEY:-/var/services/homes/tonio/.ssh/ds212j_backup_ed25519}"
DEST_DIR="${DEST_DIR:-/var/services/homes/tonio/Sauvegardes/ds212j}"

# Chemins relatifs à la racine du DS212j, conservés tels quels sous DEST_DIR.
SOURCES="/volume1/web/maison /volume1/@optware /opt/etc/init.d/S98eibd"

if [ ! -r "$SSH_KEY" ]; then
    echo "ERREUR: clé SSH illisible : $SSH_KEY" >&2
    exit 1
fi

mkdir -p "$DEST_DIR"

REMOTE_PATHS=
for path in $SOURCES; do
    REMOTE_PATHS="$REMOTE_PATHS $SOURCE_USER@$SOURCE_HOST:$path"
done

# Les dossiers temporaires d'Optware ne sont lisibles que par root et
# n'ont pas d'utilité pour une reconstruction.
# shellcheck disable=SC2086
if ! rsync -a --relative \
    --exclude='/volume1/@optware/ipkg-*' \
    --exclude='/volume1/@optware/@autoupdate' \
    --rsh="ssh -p $SOURCE_PORT -i $SSH_KEY -o BatchMode=yes -o ConnectTimeout=20" \
    $REMOTE_PATHS "$DEST_DIR/"; then
    echo "ERREUR: copie de la configuration DS212j en échec vers $DEST_DIR" >&2
    exit 1
fi

echo "Configuration DS212j copiée vers $DEST_DIR"
