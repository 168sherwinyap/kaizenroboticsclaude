#!/usr/bin/env bash
# Serve the HandLab sensor dashboard + 5-servo hand (Web Serial) on :8003.
set -e
cd "$(dirname "$0")"
. scripts/launch_common.sh
URL="http://127.0.0.1:8003/"
echo "Serving handlab/web on $URL  (Ctrl+C to stop)"
(sleep 2; open_url "$URL") &
exec "$PY" -m http.server 8003 --bind 127.0.0.1 --directory handlab/web
