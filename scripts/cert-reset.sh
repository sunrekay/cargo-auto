#!/bin/sh
# Remove every certbot lineage for a domain, including the "-0001" variants
# certbot creates when it thinks the name is already taken.
#
#   sh scripts/cert-reset.sh example.com
set -eu
DOMAIN=${1:?usage: cert-reset.sh <domain>}

found=0
for dir in "/etc/letsencrypt/live/$DOMAIN" /etc/letsencrypt/live/"$DOMAIN"-*; do
    [ -d "$dir" ] || continue
    name=$(basename "$dir")
    found=1
    echo "  removing lineage $name"
    certbot delete --cert-name "$name" --non-interactive 2>/dev/null || {
        # not a certbot lineage (a leftover directory); remove it directly
        rm -rf "$dir" "/etc/letsencrypt/archive/$name" \
               "/etc/letsencrypt/renewal/$name.conf"
    }
done

[ "$found" = 1 ] || echo "  no certificate found for $DOMAIN"
