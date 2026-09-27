#!/usr/bin/env bash
set -euo pipefail
: "${DOMAIN:?DOMAIN is not set}"
: "${ACME_EMAIL:?ACME_EMAIL is not set}"
compose=("$DOCKER" compose -f docker-compose.prod.yml)
flags=()
[[ ${STAGING:-0} == 1 ]] && flags+=(--staging)
# Never silently reuse a staging lineage for a production deployment.
issuer=$("${compose[@]}" exec -T nginx sh -c 'openssl x509 -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" -noout -issuer' 2>/dev/null || true)
if [[ ${STAGING:-0} != 1 && $issuer =~ (STAGING|Fake|Pretend) ]]; then
  echo 'Staging certificate is installed. Run make prod-cert-reset, then make prod.' >&2
  exit 1
fi
if [[ ${STAGING:-0} == 1 && -n $issuer && ! $issuer =~ (STAGING|Fake|Pretend) ]]; then
  echo 'A production certificate exists. Refusing to replace it with staging.' >&2
  exit 1
fi
"${compose[@]}" run --rm --no-deps --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot --cert-name "$DOMAIN" \
  -d "$DOMAIN" --email "$ACME_EMAIL" --agree-tos --no-eff-email \
  --non-interactive --keep-until-expiring "${flags[@]}"
# Restart re-renders CERT_DIR: reload alone would keep the placeholder path.
"${compose[@]}" restart nginx
"${compose[@]}" exec -T nginx nginx -t
