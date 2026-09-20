#!/usr/bin/env bash

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." || exit 1

trap 'kill $(jobs -pr) 2>/dev/null' EXIT

python3 main.py &
(cd src/frontend && exec npm run dev) &

wait -n
