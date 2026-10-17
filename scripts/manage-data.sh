#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
DEVELOPMENT="$ROOT/vocabulary"
PRODUCTION="$ROOT/bin/vocabulary"
BACKUPS="$ROOT/backups"
LANGUAGES=(english french german)

copy_data() {
    for LANGUAGE in "${LANGUAGES[@]}"; do
        rm -rf "$2/$LANGUAGE"
        cp -R "$1/$LANGUAGE" "$2/$LANGUAGE"
    done
    mkdir -p "$2/history"
    cp "$1/history/history.db" "$2/history/history.db"
}

data_path() {
    case "$1" in
        development) echo "$DEVELOPMENT" ;;
        production) echo "$PRODUCTION" ;;
        *) return 1 ;;
    esac
}

require_environment() {
    case "$1" in
        development|production) ;;
        *) echo "The environment must be development or production, not '$1'." >&2
           exit 1 ;;
    esac
}

is_complete() {
    [ -f "$1/history/history.db" ] || return 1
    for LANGUAGE in "${LANGUAGES[@]}"; do
        [ -n "$(find "$1/$LANGUAGE" -name '*.md' -print -quit 2>/dev/null)" ] || return 1
    done
}

require_data() {
    if ! is_complete "$1"; then
        echo "There is no complete practice data at $1." >&2
        exit 1
    fi
}

count_files() {
    find "$1" -name '*.md' 2>/dev/null | wc -l | tr -d ' '
}

backup_data() {
    local NAME PENDING
    NAME="$(date +%Y-%m-%d_%H-%M-%S)${2:+_$2}"
    PENDING="$BACKUPS/$1/.pending-$NAME"
    trap 'rm -rf "$PENDING"' EXIT
    mkdir -p "$PENDING/history"
    copy_data "$(data_path "$1")" "$PENDING"
    mv "$PENDING" "$BACKUPS/$1/$NAME"
    trap - EXIT
    echo "Backed up the practice data of $1 ($(count_files "$BACKUPS/$1/$NAME") files) to $BACKUPS/$1/$NAME."
}

usage() {
    cat >&2 <<EOF
Usage: $(basename "$0") <command> [arguments]

Commands:
  copy <from> <to>                 overwrite the practice data of <to> with that of <from>, after backing up <to>
  backup <environment>             save the practice data of <environment> under backups/<environment>/<timestamp>
  restore <environment> [timestamp]
                                   restore the practice data of <environment> from a backup, after backing it up;
                                   the newest backup when no timestamp is given
  list                             show the backups of both environments

Environments: development ($DEVELOPMENT), production ($PRODUCTION)
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
        backup_data "$3" "before-copy"
        copy_data "$SOURCE" "$DESTINATION"
        echo "Copied the practice data of $SOURCE to $DESTINATION."
        ;;
    backup)
        [ $# -eq 2 ] || usage
        require_environment "$2"
        require_data "$(data_path "$2")"
        backup_data "$2"
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
        if ! is_complete "$SOURCE"; then
            echo "There is no complete backup '$NAME' under $BACKUPS/$2." >&2
            exit 1
        fi
        if is_complete "$DATA"; then
            backup_data "$2" "before-restore"
        fi
        mkdir -p "$DATA"
        copy_data "$SOURCE" "$DATA"
        echo "Restored the practice data of $DATA from $SOURCE."
        ;;
    list)
        [ $# -eq 1 ] || usage
        for ENVIRONMENT in development production; do
            echo "$ENVIRONMENT:"
            if [ -z "$(ls -1 "$BACKUPS/$ENVIRONMENT" 2>/dev/null)" ]; then
                echo "  no backups"
                continue
            fi
            for BACKUP in $(ls -1 "$BACKUPS/$ENVIRONMENT" | sort); do
                if is_complete "$BACKUPS/$ENVIRONMENT/$BACKUP"; then
                    STATE="complete"
                else
                    STATE="incomplete"
                fi
                printf '  %-36s %4s files  %s\n' "$BACKUP" "$(count_files "$BACKUPS/$ENVIRONMENT/$BACKUP")" "$STATE"
            done
        done
        ;;
    *) usage ;;
esac
