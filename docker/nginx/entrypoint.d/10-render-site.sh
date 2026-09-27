#!/bin/sh
# Render the site config, substituting only the variables listed below so that
# nginx's own $host, $remote_addr and friends survive.
set -e
: "${DOMAIN:?DOMAIN is not set}"

CONF=/etc/nginx/conf.d/default.conf

# Docker publishes its embedded DNS in the container's resolv.conf; fall back
# to the well-known address if it cannot be read.
RESOLVER=$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf 2>/dev/null)
: "${RESOLVER:=127.0.0.11}"

# The placeholder deliberately lives outside /etc/letsencrypt: a directory in
# live/ makes certbot think a lineage already exists, and it then issues into
# "<domain>-0001" which nginx would never read.
REAL_CERT="/etc/letsencrypt/live/${DOMAIN}"
PLACEHOLDER_CERT="/etc/nginx/ssl/${DOMAIN}"

if [ -s "${REAL_CERT}/fullchain.pem" ]; then
    CERT_DIR="${REAL_CERT}"
    STAPLING="on"
    echo "[nginx] using the certificate from ${REAL_CERT}"
else
    CERT_DIR="${PLACEHOLDER_CERT}"
    STAPLING="off"    # a self-signed certificate has no issuer to staple
    echo "[nginx] no certificate yet — using the placeholder"
fi

export DOMAIN RESOLVER CERT_DIR STAPLING
envsubst '${DOMAIN} ${RESOLVER} ${CERT_DIR} ${STAPLING}' \
    < /etc/nginx/site.conf.template > "$CONF"

# A container without IPv6 cannot bind [::], and nginx treats that as fatal:
# "socket() [::]:80 failed (97: Address family not supported by protocol)".
if [ ! -f /proc/net/if_inet6 ]; then
    sed -i '/listen \[::\]/d' "$CONF"
    echo "[nginx] no IPv6 in this container — IPv6 listeners removed"
fi

echo "[nginx] config rendered for ${DOMAIN} (resolver ${RESOLVER})"
