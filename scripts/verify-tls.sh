#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <domain> [expected_server_url]"
  echo "Example: $0 mrs.example.com https://mrs.example.com"
  exit 2
fi

DOMAIN="$1"
EXPECTED_URL="${2:-https://$DOMAIN}"

echo "[1/5] Checking HTTPS endpoint reachability..."
JSON=$(curl -fsS "https://$DOMAIN/.well-known/mrs")

echo "[2/5] Checking HTTP->HTTPS redirect..."
HTTP_HEADERS=$(curl -sSI "http://$DOMAIN/" | tr -d '\r')
printf "%s\n" "$HTTP_HEADERS" | grep -qi '^Location: https://' || {
  echo "ERROR: HTTP does not redirect to HTTPS"
  exit 1
}

echo "[3/5] Checking TLS certificate validity window..."
CERT_DATES=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null | openssl x509 -noout -dates)
[[ -n "$CERT_DATES" ]] || { echo "ERROR: unable to read certificate"; exit 1; }
printf "%s\n" "$CERT_DATES"

echo "[4/5] Checking advertised server URL in /.well-known/mrs..."
SERVER_URL=$(python3 - <<'PY' "$JSON"
import json,sys
print(json.loads(sys.argv[1]).get('server',''))
PY
)

echo "Advertised server URL: $SERVER_URL"
if [[ "$SERVER_URL" != "$EXPECTED_URL" ]]; then
  echo "ERROR: advertised server URL mismatch"
  echo "Expected: $EXPECTED_URL"
  exit 1
fi

echo "[5/5] Checking endpoint returns valid JSON with mrs_version..."
python3 - <<'PY' "$JSON"
import json,sys
j=json.loads(sys.argv[1])
assert 'mrs_version' in j, 'missing mrs_version'
assert 'server' in j, 'missing server'
print('mrs_version:', j['mrs_version'])
PY

echo "✅ TLS verification passed for $DOMAIN"
