#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
DEVELOPMENT="$ROOT/vocabulary"
PRODUCTION="$ROOT/bin/vocabulary"
BACKUPS="$ROOT/backups"

copy_data() {
    for LANGUAGE in english french german; do
        rm -rf "$2/$LANGUAGE"
        cp -R "$1/$LANGUAGE" "$2/$LANGUAGE"
    done
    mkdir -p "$2/history"
    cp "$1/history/history.db" "$2/history/history.db"
}

require_data() {
    if [ ! -d "$1/history" ]; then
        echo "There is no practice data at $1." >&2
        exit 1
    fi
}

require_backup() {
    if [ ! -d "$1" ] || [ ! -f "$1/history/history.db" ] || [ ! -d "$1/english" ]; then
        echo "There is no complete backup $2 under $3." >&2
        exit 1
    fi
}

usage() {
    echo "Usage: $(basename "$0") {to-production|to-development}" >&2
    echo "                    {dev|prod} backup" >&2
    echo "                    {dev|prod} restore [name]" >&2
    echo "  to-production  copy $DEVELOPMENT to $PRODUCTION" >&2
    echo "  to-development copy $PRODUCTION to $DEVELOPMENT" >&2
    echo "  dev backup     save $DEVELOPMENT under $BACKUPS/dev" >&2
    echo "  prod backup    save $PRODUCTION under $BACKUPS/prod" >&2
    echo "  dev restore    restore $DEVELOPMENT from $BACKUPS/dev (the newest backup, or [name])" >&2
    echo "  prod restore   restore $PRODUCTION from $BACKUPS/prod (the newest backup, or [name])" >&2
    exit 1
}

case "${1:-}" in
    to-production) SOURCE="$DEVELOPMENT"; DESTINATION="$PRODUCTION" ;;
    to-development) SOURCE="$PRODUCTION"; DESTINATION="$DEVELOPMENT" ;;
    dev|prod)
        if [ "$1" = dev ]; then DATA="$DEVELOPMENT"; else DATA="$PRODUCTION"; fi
        case "${2:-}" in
            backup)
                require_data "$DATA"
                NAME="$(date +%Y-%m-%d_%H-%M-%S)"
                PENDING="$BACKUPS/$1/.pending-$NAME"
                trap 'rm -rf "$PENDING"' EXIT
                mkdir -p "$PENDING/history"
                copy_data "$DATA" "$PENDING"
                mv "$PENDING" "$BACKUPS/$1/$NAME"
                trap - EXIT
                echo "Backed up $DATA to $BACKUPS/$1/$NAME."
                exit 0
                ;;
            restore)
                NAME="${3:-}"
                if [ -z "$NAME" ]; then
                    NAME="$(ls -1 "$BACKUPS/$1" 2>/dev/null | sort | tail -n 1 || true)"
                    if [ -z "$NAME" ]; then
                        echo "There are no backups under $BACKUPS/$1." >&2
                        exit 1
                    fi
                fi
                SOURCE="$BACKUPS/$1/$NAME"
                require_backup "$SOURCE" "$NAME" "$BACKUPS/$1"
                copy_data "$SOURCE" "$DATA"
                echo "Restored $DATA from $SOURCE."
                exit 0
                ;;
            *) usage ;;
        esac
        ;;
    *) usage ;;
esac

for DIRECTION in "$SOURCE" "$DESTINATION"; do
    require_data "$DIRECTION"
done

if [ "$(cd "$SOURCE" && pwd -P)" = "$(cd "$DESTINATION" && pwd -P)" ]; then
    echo "Source and destination are the same." >&2
    exit 1
fi

copy_data "$SOURCE" "$DESTINATION"

echo "Overwrote the practice data of $DESTINATION with the data of $SOURCE."
