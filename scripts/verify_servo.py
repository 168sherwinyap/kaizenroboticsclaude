#!/usr/bin/env python3
"""Verify faces + S1 servo over the MicroPython REPL (cross-platform).

Replaces the old ``verify_servo.ps1``. Sends each key, reads the board's echo,
then reads the PCA9685 channel-8 OFF value and the LED-matrix pixels back from
the chip so the result does not depend on eyeballing the display.

Run:  python scripts/verify_servo.py [--port /dev/...]
"""

import argparse
import os
import sys
import time

import serial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import microbit_util

CR = b"\r"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", "-p", default="", help="serial port (default: auto-detect)")
    args = ap.parse_args()

    port = args.port or microbit_util.find_serial_port()
    if not port:
        sys.exit("No micro:bit serial port found. Plug the board in, or pass --port.")

    try:
        ser = serial.Serial(port, 115200, timeout=3)
    except Exception as exc:
        sys.exit("Could not open %s: %s" % (port, exc))

    def read_available():
        return ser.read(ser.in_waiting).decode("ascii", "replace")

    def drain(ms=0.9):
        time.sleep(ms)
        return read_available()

    def send(line):
        ser.write((line + "\r").encode("ascii"))
        time.sleep(0.25)

    def probe():
        send("i2c.write(0x40, bytes([0x26]))")
        send("d = i2c.read(0x40, 4)")
        send("print('CH8', d[2] | (d[3] << 8))")
        send("print('FACE', display.get_pixel(0,3), display.get_pixel(0,4))")
        send("print('SHAPE', display.get_pixel(0,1), display.get_pixel(2,2), display.get_pixel(2,0))")
        return drain(0.8)

    def keytest(key):
        ser.write(b"\x04")                       # soft reset -> main.py
        time.sleep(3.2)
        drain(0.3)
        ser.write(key.encode("ascii"))
        echo = drain(0.7)
        ser.write(b"\x03")                       # Ctrl-C -> REPL
        drain(1.4)
        return echo, probe()

    try:
        time.sleep(1.2)
        ser.write(b"\x03")
        drain(1.2)

        # PCA9685 presence and prescale.
        send("print('SCAN', i2c.scan())")
        send("i2c.write(0x40, bytes([0xFE]))")
        send("print('PRESCALE', i2c.read(0x40, 1)[0])")
        presence = drain(1.0)

        k_echo, k_probe = keytest("k")
        j_echo, j_probe = keytest("j")
        r_echo, r_probe = keytest("r")
        x_echo, x_probe = keytest("x")

        ser.write(b"\x04")                       # leave the board running main.py
        time.sleep(3.0)
    finally:
        ser.close()

    print("---PORT---")
    print(port)
    print("---PCA9685---")
    print(presence)
    print("---AFTER_K---")
    print(k_echo)
    print(k_probe)
    print("---AFTER_J---")
    print(j_echo)
    print(j_probe)
    print("---AFTER_R---")
    print(r_echo)
    print(r_probe)
    print("---AFTER_X---")
    print(x_echo)
    print(x_probe)


if __name__ == "__main__":
    main()
