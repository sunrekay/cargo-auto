#!/bin/sh
# Fail loudly and early: without this a bad config surfaces only as a container
# that restarts forever, which looks like a networking problem rather than a
# configuration one.
set -e
if ! output=$(nginx -t 2>&1); then
    printf '%s\n' "$output"
    echo "[nginx] configuration is invalid — see the errors above"
    exit 1
fi
