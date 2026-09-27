#!/bin/sh
# Render the site config, substituting only ${DOMAIN} so that nginx's own
# $host, $remote_addr and friends survive.
set -e
: "${DOMAIN:?DOMAIN is not set}"

CONF=/etc/nginx/conf.d/default.conf
envsubst '${DOMAIN}' < /etc/nginx/site.conf.template > "$CONF"

# A container without IPv6 cannot bind [::], and nginx treats that as fatal:
# "socket() [::]:80 failed (97: Address family not supported by protocol)".
# The stock image does the same check for its own default config.
if [ ! -f /proc/net/if_inet6 ]; then
    sed -i '/listen \[::\]/d' "$CONF"
    echo "[nginx] no IPv6 in this container — IPv6 listeners removed"
fi

echo "[nginx] config rendered for ${DOMAIN}"
