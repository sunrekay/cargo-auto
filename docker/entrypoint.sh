#!/usr/bin/env bash
# Boots a virtual X display plus a VNC bridge, then runs the given command.
# The display exists so Chromium can run headed (and so a person can take over
# the browser through noVNC when the site asks for a human check).
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
SCREEN="${SCREEN:-1600x1000x24}"

if [ "${ENABLE_VNC:-1}" = "1" ]; then
  Xvfb "$DISPLAY" -screen 0 "$SCREEN" -nolisten tcp >/tmp/xvfb.log 2>&1 &
  for _ in $(seq 1 60); do
    xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && break
    sleep 0.25
  done
  xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 || { echo "[vnc] Xvfb failed:"; cat /tmp/xvfb.log; exit 1; }

  x11vnc -display "$DISPLAY" -forever -shared -nopw -quiet -rfbport 5900 \
         >/tmp/x11vnc.log 2>&1 &
  websockify --web=/usr/share/novnc 6080 localhost:5900 >/tmp/novnc.log 2>&1 &

  echo "[vnc] live browser at  ->  http://localhost:6080/"
  echo "[vnc] (click into the page there to pass the site's human check)"
fi

exec "$@"
