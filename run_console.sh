#!/bin/bash
set -euo pipefail

python_bin="/usr/local/bin/python3"

if [[ ! -x "$python_bin" || -d "$python_bin" ]]; then
    printf 'Error: No executable Python 3 interpreter found at %s\n' "$python_bin" >&2
    exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$script_dir"
exec "$python_bin" "$script_dir/main_console.py" "$@"
