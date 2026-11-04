#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d frontend/node_modules ]; then
    (cd frontend && npm install)
fi

if [ ! -f frontend/dist/index.html ] || [ -n "$(find frontend/src frontend/public frontend/index.html frontend/package.json -newer frontend/dist/index.html -print -quit)" ]; then
    (cd frontend && npm run build)
fi

if [ -z "${VIRTUAL_ENV:-}" ] && [ -x bin/.venv/bin/python ]; then
    exec bin/.venv/bin/python scripts/run_web.py "$@"
fi
exec python3 scripts/run_web.py "$@"
