#!/usr/bin/env bash
# Ordered deployment, following genmail_server/scripts/prod-start.sh.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
step() { printf '\n==> %s\n' "$*"; }
trap 'echo "Deployment failed. Inspect: make prod-logs. Fix the reported error and repeat make prod." >&2' ERR
make_cmd="${MAKE:-make}"
step '1/6 Preflight checks'
"$make_cmd" --no-print-directory prod-init
step '2/6 Build API and proxy'
"$DOCKER" compose -f docker-compose.prod.yml build api nginx
step '3/6 Start services and wait for the API'
if [[ ${DATABASE_URL:-} =~ @postgres(:5432)?/ ]]; then
  "$DOCKER" compose -f docker-compose.prod.yml --profile postgres up -d --wait --wait-timeout 180 postgres
fi
"$DOCKER" compose -f docker-compose.prod.yml up -d --wait --wait-timeout 180 api nginx
step '4/6 Public certificate'
"$make_cmd" --no-print-directory prod-cert-issue
"$DOCKER" compose -f docker-compose.prod.yml up -d certbot
step '5/6 Verify public routes'
"$make_cmd" --no-print-directory prod-verify
if [[ ${STAGING:-0} == 1 ]]; then
  step '6/6 Staging rehearsal completed (not production-ready TLS)'
else
  step '6/6 Ready'
fi
printf 'Site: https://%s/\nAPI: https://%s/api/cars\nUpdate: make update\nLogs: make prod-logs\n' "$DOMAIN" "$DOMAIN"
