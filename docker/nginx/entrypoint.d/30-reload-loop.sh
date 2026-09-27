#!/bin/sh
# Pick up a certificate renewed by certbot without restarting the container.
# Runs in the background: the entrypoint execs nginx after these scripts, and
# this loop keeps running alongside it.
set -e
(
    while :; do
        sleep 6h
        nginx -s reload 2>/dev/null || true
    done
) &
echo "[nginx] certificate reload loop started (every 6h)"
