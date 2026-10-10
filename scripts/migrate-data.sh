#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
DEVELOPMENT="$ROOT/vocabulary"
PRODUCTION="$ROOT/bin/vocabulary"

case "${1:-}" in
    to-production) SOURCE="$DEVELOPMENT"; DESTINATION="$PRODUCTION" ;;
    to-development) SOURCE="$PRODUCTION"; DESTINATION="$DEVELOPMENT" ;;
    *) echo "Usage: $(basename "$0") {to-production|to-development}" >&2
       echo "  to-production  copy $DEVELOPMENT to $PRODUCTION" >&2
       echo "  to-development copy $PRODUCTION to $DEVELOPMENT" >&2
       exit 1 ;;
esac

for DIRECTION in "$SOURCE" "$DESTINATION"; do
    if [ ! -d "$DIRECTION/history" ]; then
        echo "There is no practice data at $DIRECTION." >&2
        exit 1
    fi
done

if [ "$(cd "$SOURCE" && pwd -P)" = "$(cd "$DESTINATION" && pwd -P)" ]; then
    echo "Source and destination are the same." >&2
    exit 1
fi

for LANGUAGE in english french german; do
    rm -rf "$DESTINATION/$LANGUAGE"
    cp -R "$SOURCE/$LANGUAGE" "$DESTINATION/$LANGUAGE"
done

mkdir -p "$DESTINATION/history"
cp "$SOURCE/history/history.db" "$DESTINATION/history/history.db"

echo "Overwrote the practice data of $DESTINATION with the data of $SOURCE."
