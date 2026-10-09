#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"
BUILD="$ROOT/bin/.build"
VENV="$ROOT/bin/.venv"
EXECUTABLE="$ROOT/bin/languages"

if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi
if [ ! -f "$VENV/.installed" ] || [ requirements.txt -nt "$VENV/.installed" ]; then
    "$VENV/bin/python" -m pip install --quiet --upgrade pip
    "$VENV/bin/python" -m pip install --quiet -r requirements.txt pyinstaller
    touch "$VENV/.installed"
fi

if [ ! -d frontend/node_modules ]; then
    (cd frontend && npm install)
fi

if [ ! -x "$EXECUTABLE" ] || [ -n "$(find src backend frontend/src frontend/public frontend/index.html frontend/package.json bin/launcher.py requirements.txt -newer "$EXECUTABLE" -print -quit)" ]; then
    (cd frontend && npm run typecheck && npx vite build --outDir "$BUILD/dist" --emptyOutDir)
    "$VENV/bin/pyinstaller" --noconfirm --log-level WARN --onefile --name languages \
        --distpath "$ROOT/bin" --workpath "$BUILD/work" --specpath "$BUILD" --paths "$ROOT" \
        --add-data "$BUILD/dist:frontend/dist" --collect-submodules uvicorn --collect-all faker \
        "$ROOT/bin/launcher.py"
fi

"$VENV/bin/python" bin/seed.py

if [ ! -f bin/.env ]; then
    if [ -f .env ]; then
        cp .env bin/.env
    else
        echo "No API key: put OPENAI_API_KEY=... in bin/.env, or start with --demo."
    fi
fi

exec "$EXECUTABLE" "$@"
