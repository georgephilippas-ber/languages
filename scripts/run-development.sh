#!/usr/bin/env bash

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." || exit 1

# Give each server its own process group, including its child processes.
set -m
pids=()
trap 'for pid in "${pids[@]}"; do kill -TERM -- "-$pid" 2>/dev/null; done; wait' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

/usr/bin/python3 main.py &
pids+=("$!")
(cd src/frontend && exec npm run dev) &
pids+=("$!")

wait
