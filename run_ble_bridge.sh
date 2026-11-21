#!/usr/bin/env bash
# macOS/Linux launcher for ble_keyboard_bridge.py.
set -e
cd "$(dirname "$0")"
. scripts/launch_common.sh
exec "$PY" ble_keyboard_bridge.py "$@"
