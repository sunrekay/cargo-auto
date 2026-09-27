#!/bin/sh
# Report every process listening on 80 and 443.
#
# More than one listener matters: a server bound to a specific address takes
# precedence over docker's 0.0.0.0 binding, so a host nginx can silently
# swallow all external traffic while the container looks healthy and docker
# never reports a port conflict.
set -u

PORTS=${*:-80 443}

listeners() {
    port=$1
    if command -v ss >/dev/null 2>&1; then
        ss -lptnH "sport = :$port" 2>/dev/null |
            while read -r line; do
                addr=$(echo "$line" | awk '{print $4}')
                proc=$(echo "$line" | sed -n 's/.*users:((\("[^"]*"\).*/\1/p' | tr -d '"')
                [ -z "$proc" ] && proc="unknown"
                echo "$proc $addr"
            done
    elif command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $1, $9}'
    fi
}

for port in $PORTS; do
    found=$(listeners "$port")
    if [ -z "$found" ]; then
        echo "  port $port: free"
        continue
    fi

    echo "$found" | while read -r proc addr; do
        [ -z "$proc" ] && continue
        echo "  port $port: $proc on $addr"
    done

    count=$(echo "$found" | grep -c .)
    if [ "$count" -gt 1 ]; then
        echo "  warning: $count listeners on port $port."
        echo "           A server bound to one address beats docker on 0.0.0.0,"
        echo "           so requests may never reach the container while docker"
        echo "           still reports no conflict. Stop the other server, e.g."
        echo "           systemctl disable --now nginx"
    fi
done
