"""Print everything the board writes to its USB serial port for N seconds.

Usage:
    python scripts/serial_watch.py            # auto-detect the port, 120 s
    python scripts/serial_watch.py 5          # auto-detect the port, 5 s
    python scripts/serial_watch.py <port> 5   # a named port, 5 s
"""
import os
import sys
import time

import serial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import microbit_util

args = sys.argv[1:]
# A lone number is the duration, not a port.
if len(args) == 1 and args[0].isdigit():
    args = ["", args[0]]
PORT = (args[0] if args else "") or microbit_util.find_serial_port()
if not PORT:
    sys.exit("No micro:bit serial port found. Pass one, or plug the board in.")
SECONDS = int(args[1]) if len(args) > 1 else 120

try:
    s = serial.Serial(PORT, 115200, timeout=0.5)
except Exception as exc:
    sys.exit("Cannot open %s: %s\nIs a browser page, a bridge or a probe holding the port?" % (PORT, exc))
start = time.time()
while time.time() - start < SECONDS:
    data = s.read(256)
    if data:
        print("[%s] %r" % (time.strftime("%H:%M:%S"), data), flush=True)
print("watch finished", flush=True)
s.close()
