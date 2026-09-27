#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
: "${DOMAIN:?DOMAIN is not set}"
: "${ACME_EMAIL:?ACME_EMAIL is not set}"
compose=("$DOCKER" compose -f docker-compose.prod.yml)
[[ ${PROD_DEPLOY:-0} == 1 ]] || "${compose[@]}" build certbot
helper() { "${compose[@]}" run --rm --no-deps --entrypoint python3 certbot /opt/certificate.py "$1"; }
kind=$(helper state)
case "$kind:${STAGING:-0}" in
  staging:0) echo 'Staging lineage installed. Inspect and run make prod-cert-reset before production.' >&2; exit 1 ;;
  production:1) echo 'Refusing to replace a production certificate with staging.' >&2; exit 1 ;;
esac
# A reusable certificate must pass hostname, key, expiry and chain validation.
if [[ $kind != missing && $kind != selfsigned ]] && helper ready; then
  helper publish
  if [[ ${PROD_DEPLOY:-0} != 1 ]] && [[ -n $("${compose[@]}" ps --status running -q nginx) ]]; then
    "${compose[@]}" up -d --no-deps nginx
    "${compose[@]}" exec -T nginx sh -c 'nginx -t && nginx -s reload'
  fi
  exit 0
fi
was_nginx=$("${compose[@]}" ps --status running -q nginx)
was_certbot=$("${compose[@]}" ps --status running -q certbot)
restore_on_failure() {
  rc=$?
  if [[ $rc != 0 ]]; then
    echo 'Certificate issuance failed; restoring previously running containers.' >&2
    [[ -z $was_nginx ]] || "${compose[@]}" start nginx || true
    [[ -z $was_certbot ]] || "${compose[@]}" start certbot || true
  fi
  return "$rc"
}
trap restore_on_failure EXIT
# Stop only this project's proxy/renewal worker, never an unrelated host service.
"${compose[@]}" stop certbot nginx
helper prepare
flags=()
[[ ${STAGING:-0} == 1 ]] && flags+=(--staging)
"${compose[@]}" run --rm --no-deps -p 80:80 --entrypoint certbot certbot certonly \
  --standalone --cert-name "$DOMAIN" -d "$DOMAIN" --email "$ACME_EMAIL" \
  --agree-tos --no-eff-email --non-interactive --keep-until-expiring "${flags[@]}"
helper publish
if [[ ${PROD_DEPLOY:-0} != 1 && -n $was_nginx ]]; then
  "${compose[@]}" up -d --no-deps nginx
  "${compose[@]}" exec -T nginx nginx -t
  [[ -z $was_certbot ]] || "${compose[@]}" up -d --no-deps certbot
fi
