#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
python3 -m pip install -r requirements.txt
cd src/frontend
npm install
