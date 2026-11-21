#!/usr/bin/env bash
# Serve the Sonar Sentinel radar (Web Serial) on :8002.
set -e
cd "$(dirname "$0")"
. scripts/launch_common.sh
URL="http://127.0.0.1:8002/"
echo "Serving sentinel/web on $URL  (Ctrl+C to stop)"
(sleep 2; open_url "$URL") &
exec "$PY" -m http.server 8002 --bind 127.0.0.1 --directory sentinel/web
