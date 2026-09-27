#!/bin/sh
set -eu
trap 'exit 0' TERM INT
while :; do
    # Override standalone stored by initial issuance. nginx remains online.
    certbot renew --cert-name "$DOMAIN" --webroot -w /var/www/certbot \
        --non-interactive --deploy-hook 'python3 /opt/certificate.py publish' \
        || echo 'Certificate renewal failed; existing published pair retained' >&2
    sleep 12h & wait $!
done
