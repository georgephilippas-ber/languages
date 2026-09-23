#!/bin/bash
set -euo pipefail

if [[ $# -gt 1 ]] || { [[ $# -eq 1 ]] && [[ ! "$1" =~ ^[0-9]+$ || ! "$1" =~ [1-9] ]]; }; then
    printf 'Usage: %s [positive-number-of-questions]\n' "$0" >&2
    exit 2
fi

python_bin="/usr/local/bin/python3"

if [[ ! -x "$python_bin" || -d "$python_bin" ]]; then
    printf 'Error: No executable Python 3 interpreter found at %s\n' "$python_bin" >&2
    exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$script_dir"
exec "$python_bin" "$script_dir/main_console.py" "$@"
