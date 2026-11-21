#!/usr/bin/env bash
# One-time setup on macOS/Linux: a private Python environment in .venv with the
# packages the PC-side tools need. Run once after cloning:  ./setup.sh
#
# A venv is used because Homebrew's Python refuses a plain `pip install`
# (PEP 668), and a stock Mac has `python3` but no `python` or `pip` command.
set -e
cd "$(dirname "$0")"
command -v python3 >/dev/null 2>&1 || {
  echo "python3 not found. On macOS run: xcode-select --install"; exit 1; }
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
.venv/bin/python -c "import serial, bleak, pynput; print('Setup done. Use .venv/bin/python to run the scripts.')"
