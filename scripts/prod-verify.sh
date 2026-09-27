#!/usr/bin/env bash
set -euo pipefail
: "${DOMAIN:?DOMAIN is not set}"
# Staging certificates are intentionally untrusted: do not report production
# success, nor bypass browser/public TLS verification with curl -k.
if [[ ${STAGING:-0} == 1 ]]; then
  echo 'Staging rehearsal: checking API internally; public HTTPS is NOT trusted.'
  "$DOCKER" compose -f docker-compose.prod.yml exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=5)"
  exit 0
fi
for path in /api/health / /api/cars; do
  ok=0
  for ((i=0; i<30; i++)); do
    if curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "https://${DOMAIN}${path}" >/dev/null 2>&1; then ok=1; break; fi
    sleep 2
  done
  [[ $ok == 1 ]] || { echo "Public check failed: https://${DOMAIN}${path}. Check DNS, TLS and make prod-logs." >&2; exit 1; }
  echo "OK: https://${DOMAIN}${path}"
done
