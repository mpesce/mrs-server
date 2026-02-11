#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

source .venv/bin/activate

pytest -q

python -m mrs_server.main --host 127.0.0.1 --port 8000 >/tmp/mrs-server-verify.log 2>&1 &
PID=$!
trap 'kill $PID >/dev/null 2>&1 || true' EXIT

for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/.well-known/mrs >/dev/null 2>&1; then
    echo "OK: mrs-server verify complete"
    exit 0
  fi
  sleep 0.5
done

echo "ERROR: server failed health check"
exit 1
