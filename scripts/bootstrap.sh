#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -U pip
pip install -e ".[dev]"

python scripts/init_db.py

echo "OK: mrs-server bootstrap complete"
