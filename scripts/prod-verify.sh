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
error_file=$(mktemp)
trap 'rm -f "$error_file"' EXIT
for path in /api/health / /api/cars; do
  ok=0
  for ((i=0; i<30; i++)); do
    if curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "https://${DOMAIN}${path}" >/dev/null 2>"$error_file"; then ok=1; break; else status=$?; fi
    # Certificate failures will not heal while retrying the same certificate.
    [[ $status != 60 ]] || break
    sleep 2
  done
  if [[ $ok != 1 ]]; then
    echo "Public check failed: https://${DOMAIN}${path} (curl exit $status)." >&2
    cat "$error_file" >&2
    if [[ $status == 60 ]]; then
      echo 'TLS certificate is not trusted. Inspect make prod-cert, then run make prod-cert-issue. Do not disable TLS verification.' >&2
    else
      echo 'Check DNS, network access and make prod-logs.' >&2
    fi
    exit 1
  fi
  echo "OK: https://${DOMAIN}${path}"
done
