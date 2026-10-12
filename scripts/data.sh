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

data_path() {
    case "$1" in
        dev) echo "$DEVELOPMENT" ;;
        prod) echo "$PRODUCTION" ;;
        *) return 1 ;;
    esac
}

require_environment() {
    case "$1" in
        dev|prod) ;;
        *) echo "The environment must be dev or prod, not '$1'." >&2
           exit 1 ;;
    esac
}

require_data() {
    if [ ! -d "$1/history" ]; then
        echo "There is no practice data at $1." >&2
        exit 1
    fi
}

require_backup() {
    if [ ! -d "$1" ] || [ ! -f "$1/history/history.db" ] || [ ! -d "$1/english" ]; then
        echo "There is no complete backup '$2' under $3." >&2
        exit 1
    fi
}

usage() {
    cat >&2 <<EOF
Usage: $(basename "$0") <command> [arguments]

Commands:
  copy <from> <to>      overwrite the practice data of <to> with that of <from>
  backup <env>          save the practice data of <env> under backups/<env>/<timestamp>
  restore <env> [name]  restore the practice data of <env> from a backup; the newest when no name is given

Environments: dev ($DEVELOPMENT), prod ($PRODUCTION)
EOF
    exit 1
}

[ $# -ge 1 ] || usage

case "$1" in
    copy)
        [ $# -eq 3 ] || usage
        require_environment "$2"
        require_environment "$3"
        SOURCE="$(data_path "$2")"
        DESTINATION="$(data_path "$3")"
        require_data "$SOURCE"
        require_data "$DESTINATION"
        if [ "$(cd "$SOURCE" && pwd -P)" = "$(cd "$DESTINATION" && pwd -P)" ]; then
            echo "Source and destination are the same." >&2
            exit 1
        fi
        copy_data "$SOURCE" "$DESTINATION"
        echo "Copied the practice data of $SOURCE to $DESTINATION."
        ;;
    backup)
        [ $# -eq 2 ] || usage
        require_environment "$2"
        DATA="$(data_path "$2")"
        require_data "$DATA"
        NAME="$(date +%Y-%m-%d_%H-%M-%S)"
        PENDING="$BACKUPS/$2/.pending-$NAME"
        trap 'rm -rf "$PENDING"' EXIT
        mkdir -p "$PENDING/history"
        copy_data "$DATA" "$PENDING"
        mv "$PENDING" "$BACKUPS/$2/$NAME"
        trap - EXIT
        echo "Backed up the practice data of $DATA to $BACKUPS/$2/$NAME."
        ;;
    restore)
        { [ $# -eq 2 ] || [ $# -eq 3 ]; } || usage
        require_environment "$2"
        DATA="$(data_path "$2")"
        NAME="${3:-}"
        if [ -z "$NAME" ]; then
            NAME="$(ls -1 "$BACKUPS/$2" 2>/dev/null | sort | tail -n 1 || true)"
            if [ -z "$NAME" ]; then
                echo "There are no backups under $BACKUPS/$2." >&2
                exit 1
            fi
        fi
        SOURCE="$BACKUPS/$2/$NAME"
        require_backup "$SOURCE" "$NAME" "$BACKUPS/$2"
        copy_data "$SOURCE" "$DATA"
        echo "Restored the practice data of $DATA from $SOURCE."
        ;;
    *) usage ;;
esac
