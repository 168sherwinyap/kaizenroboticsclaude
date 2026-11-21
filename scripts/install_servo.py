#!/usr/bin/env python3
"""Upload main.py onto the micro:bit over the MicroPython REPL (cross-platform).

Replaces the old ``install_servo.ps1``. Opens the port, breaks into the REPL,
paste-mode writes ``main.py`` line by line, then checks ``FILES``/``LEN`` and
soft-resets into the new program.

Run:  python scripts/install_servo.py [--port /dev/...]
"""

import argparse
import os
import sys
import time

import serial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import microbit_util


def read_available(ser):
    """Non-blocking read of whatever has arrived (mirrors ReadExisting)."""
    return ser.read(ser.in_waiting).decode("ascii", "replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", "-p", default="", help="serial port (default: auto-detect)")
    args = ap.parse_args()

    port = args.port or microbit_util.find_serial_port()
    if not port:
        sys.exit("No micro:bit serial port found. Plug the board in, or pass --port.")

    src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
    with open(src_path, "r", encoding="utf-8") as f:
        src = f.read()
    src = src.replace("\r\n", "\n").replace("\r", "\n")
    if "'''" in src:
        sys.exit("main.py must not contain triple quotes (''' or \"\"\").")

    # Build the paste payload: write main.py from the REPL into the board's
    # filesystem, then report how many bytes landed.
    py = ("prog = r'''" + src + "'''\n"
          "with open('main.py', 'w') as f:\n"
          "    f.write(prog)\n"
          "print('SAVED', len(prog))")

    try:
        ser = serial.Serial(port, 115200, timeout=3)
    except Exception as exc:
        sys.exit("Could not open %s: %s\nStop any keyboard bridge or serial monitor first." % (port, exc))

    try:
        time.sleep(1.2)
        ser.write(b"\x03")                       # Ctrl-C -> REPL
        time.sleep(1.2)
        read_available(ser)

        ser.write(b"\x05")                       # Ctrl-E -> paste mode
        time.sleep(0.3)
        for line in py.split("\n"):
            ser.write((line + "\n").encode("ascii"))
            time.sleep(0.04)

        ser.write(b"\x04")                       # Ctrl-D -> execute paste
        time.sleep(1.0)
        save = read_available(ser)

        ser.write(b"import os\r")
        ser.write(b"print('FILES', os.listdir(), 'LEN', len(open('main.py').read()))\r")
        time.sleep(0.8)
        check = read_available(ser)

        ser.write(b"\x04")                       # Ctrl-D -> soft reset, runs main.py
        time.sleep(3.5)
        boot = read_available(ser)
    finally:
        ser.close()

    print("---PORT---")
    print(port)
    print("---SAVE---")
    print(save)
    print("---CHECK---")
    print(check)
    print("---BOOT---")
    print(boot)


if __name__ == "__main__":
    main()
