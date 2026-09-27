#!/bin/sh
# nginx refuses to start when ssl_certificate points at a missing file, and
# certbot cannot obtain a certificate until nginx is answering on port 80.
# A self-signed placeholder breaks that circle; certbot overwrites it.
set -e
: "${DOMAIN:?DOMAIN is not set}"
DIR="/etc/letsencrypt/live/${DOMAIN}"

if [ -s "${DIR}/fullchain.pem" ] && [ -s "${DIR}/privkey.pem" ]; then
    echo "[nginx] certificate present for ${DOMAIN}"
    exit 0
fi

echo "[nginx] no certificate yet — generating a self-signed placeholder"
mkdir -p "${DIR}"
openssl req -x509 -nodes -newkey rsa:2048 -days 3 \
    -keyout "${DIR}/privkey.pem" \
    -out "${DIR}/fullchain.pem" \
    -subj "/CN=${DOMAIN}" >/dev/null 2>&1
echo "[nginx] placeholder in place; run 'make prod-cert-issue' for a real one"
