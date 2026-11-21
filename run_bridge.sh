#!/usr/bin/env bash
# macOS/Linux launcher for keyboard_bridge.py.
set -e
cd "$(dirname "$0")"
. scripts/launch_common.sh
exec "$PY" keyboard_bridge.py "$@"
