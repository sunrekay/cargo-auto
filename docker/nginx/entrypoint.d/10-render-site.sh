#!/bin/sh
# Render the site config, substituting only ${DOMAIN} so that nginx's own
# $host, $remote_addr and friends survive.
set -e
: "${DOMAIN:?DOMAIN is not set}"
envsubst '${DOMAIN}' \
    < /etc/nginx/site.conf.template \
    > /etc/nginx/conf.d/default.conf
echo "[nginx] config rendered for ${DOMAIN}"
