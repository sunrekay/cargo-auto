#!/bin/sh
# Generate the self-signed placeholder the rendered config falls back to.
# Kept outside /etc/letsencrypt so certbot does not mistake it for one of its
# own lineages and issue into "<domain>-0001" instead.
set -e
: "${DOMAIN:?DOMAIN is not set}"

if [ -s "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    exit 0                      # a real certificate is in use
fi

DIR="/etc/nginx/ssl/${DOMAIN}"
[ -s "${DIR}/fullchain.pem" ] && exit 0

mkdir -p "${DIR}"
openssl req -x509 -nodes -newkey rsa:2048 -days 3 \
    -keyout "${DIR}/privkey.pem" \
    -out "${DIR}/fullchain.pem" \
    -subj "/CN=${DOMAIN}" >/dev/null 2>&1
echo "[nginx] placeholder certificate generated; run 'make prod-cert-issue' for a real one"
