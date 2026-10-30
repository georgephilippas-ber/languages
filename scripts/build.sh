#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
BUILD="$ROOT/bin/.build"
VENV="$ROOT/bin/.venv"
APP="$ROOT/bin/.dist/languages/languages"

if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi
if [ ! -f "$VENV/.installed" ] || [ requirements.txt -nt "$VENV/.installed" ]; then
    "$VENV/bin/python" -m pip install --quiet --upgrade pip
    "$VENV/bin/python" -m pip install --quiet -r requirements.txt pyinstaller
    touch "$VENV/.installed"
fi

if [ ! -d frontend/node_modules ]; then
    (cd frontend && npm ci)
fi

if [ ! -x "$APP" ] || [ -n "$(find src backend frontend/src frontend/public frontend/index.html frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.json bin/launcher.py requirements.txt scripts/build.sh -newer "$APP" -print -quit)" ]; then
    (cd frontend && npm run typecheck && npx vite build --outDir "$BUILD/dist" --emptyOutDir)
    "$VENV/bin/pyinstaller" --noconfirm --log-level WARN --onedir --name languages \
        --distpath "$ROOT/bin/.dist" --workpath "$BUILD/work" --specpath "$BUILD" --paths "$ROOT" \
        --add-data "$BUILD/dist:frontend/dist" --collect-submodules uvicorn \
        "$ROOT/bin/launcher.py"
fi

"$ROOT/scripts/make-app.sh"
echo "Move bin/Languages.app to Applications or anywhere else. Data stays in ~/tmp/languages."
