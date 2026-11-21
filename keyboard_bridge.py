#!/usr/bin/env python3
"""Global keyboard -> micro:bit faces + S1 servo, over USB serial.

Cross-platform replacement for the old ``keyboard_bridge.ps1``.

Press the keys anywhere (they are captured globally):
    k -> smile + S1 90 deg    j -> frown + S1 0 deg
    r -> circle + S1 0 deg    x -> cross + S1 180 deg

Keys are captured with ``pynput``. On macOS, grant the terminal "Accessibility"
permission the first time (System Settings -> Privacy & Security ->
Accessibility). Stop with Ctrl+C.

Run:  python keyboard_bridge.py [--port /dev/...] [--seconds N]
"""

import argparse
import os
import sys
import threading
import time

import serial

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import microbit_util

try:
    from pynput import keyboard
except ImportError:
    keyboard = None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", "-p", default="", help="serial port (default: auto-detect)")
    ap.add_argument("--seconds", "-s", type=float, default=0, help="stop after N seconds (0 = run forever)")
    ap.add_argument("--smile-key", default="k", help="key for smile + 90 deg")
    ap.add_argument("--frown-key", default="j", help="key for frown + 0 deg")
    ap.add_argument("--circle-key", default="r", help="key for circle + 0 deg")
    ap.add_argument("--cross-key", default="x", help="key for cross + 180 deg")
    args = ap.parse_args()

    mapping = {
        args.smile_key: ("k", "smile + 90"),
        args.frown_key: ("j", "frown + 0"),
        args.circle_key: ("r", "circle + 0"),
        args.cross_key: ("x", "cross + 180"),
    }

    port = args.port or microbit_util.find_serial_port()
    if not port:
        sys.exit("No micro:bit serial port found. Plug the board in, or pass --port.")

    if keyboard is None:
        sys.exit("pynput is required: pip install pynput")

    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
    except Exception as exc:
        sys.exit("Could not open %s: %s\nClose anything else using the port first." % (port, exc))

    held = set()
    lock = threading.Lock()
    stop = threading.Event()

    def on_press(key):
        try:
            ch = key.char
        except AttributeError:
            return
        if not ch:
            return
        with lock:
            if ch in held:
                return  # OS auto-repeat: already sent on the key-down edge
            cmd, what = mapping.get(ch, (None, None))
            if cmd is None:
                return
            held.add(ch)
        try:
            ser.write(cmd.encode("ascii"))
            print("sent %s (%s)" % (cmd, what), flush=True)
        except Exception as exc:
            print("Serial write failed: %s" % exc, flush=True)
            stop.set()

    def on_release(key):
        try:
            ch = key.char
        except AttributeError:
            return
        if ch:
            with lock:
                held.discard(ch)

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    try:
        listener.start()
    except Exception as exc:
        ser.close()
        sys.exit("Could not start the global key listener: %s\n"
                 "On macOS grant Accessibility permission; on Linux an X11 display is needed." % exc)

    print("micro:bit keyboard bridge on %s" % port, flush=True)
    print("  press k -> smile + 90, j -> frown + 0, r -> circle + 0, x -> cross + 180 deg.  Ctrl+C to stop.",
          flush=True)
    print("", flush=True)

    deadline = time.time() + args.seconds if args.seconds > 0 else None
    try:
        while not stop.is_set():
            if deadline and time.time() >= deadline:
                break
            try:
                data = ser.read(ser.in_waiting or 1)
            except Exception:
                break
            if data:
                text = data.decode("ascii", "replace").strip()
                if text:
                    print("micro:bit: %s" % text, flush=True)
            time.sleep(0.025)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        listener.stop()
        ser.close()
        print("Bridge stopped.", flush=True)


if __name__ == "__main__":
    main()
