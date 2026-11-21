#!/usr/bin/env bash
# Serve the Flappy Bird hand-control app (Web Serial) on :8000.
set -e
cd "$(dirname "$0")"
. scripts/launch_common.sh
URL="http://127.0.0.1:8000/"
echo "Serving flappy/web on $URL  (Ctrl+C to stop)"
(sleep 2; open_url "$URL") &
exec "$PY" -m http.server 8000 --bind 127.0.0.1 --directory flappy/web
