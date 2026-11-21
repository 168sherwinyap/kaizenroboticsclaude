#!/usr/bin/env bash
# Serve the Kaizen pushup counter (Web Serial) on :8001.
set -e
cd "$(dirname "$0")"/..
. scripts/launch_common.sh
URL="http://127.0.0.1:8001/"
echo "Serving kaizen-pushup on $URL  (Ctrl+C to stop)"
(sleep 2; open_url "$URL") &
exec "$PY" -m http.server 8001 --bind 127.0.0.1 --directory kaizen-pushup
