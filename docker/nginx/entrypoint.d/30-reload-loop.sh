#!/bin/sh
set -e
(
    previous=$(readlink /etc/nginx/public/current)
    while :; do
        sleep 60
        current=$(readlink /etc/nginx/public/current)
        if [ "$current" != "$previous" ]; then
            if nginx -t && nginx -s reload; then previous=$current; fi
        fi
    done
) &
echo "[nginx] watching published certificates (every 60s)"
