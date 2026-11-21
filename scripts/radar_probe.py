#!/usr/bin/env python3
"""Read and exercise the Sonar Sentinel USB serial protocol.

The browser page owns the serial port exclusively, so close it (or the tab) first.

Usage:
    python scripts/radar_probe.py                 # auto-detect, 12 s
    python scripts/radar_probe.py <port> 20
    python scripts/radar_probe.py <port> 25 --send "2:i;5:t:40;10:p;14:s;18:w"

Scheduled commands use "<seconds>:<command>" separated by ';'. Commands:
    i  identify (SYS:READY,PCA=OK|ERR,ALARM=0|1)
    s  start sweep          p  pause
    c  park (90 deg)        w  wiggle both servos
    t:<cm>  set keep-out distance (8..80)
"""

import argparse
import re
import statistics
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial is required: pip install pyserial")

A_RE = re.compile(r"A:(\d+),D:(\d+)")


def find_port():
    for p in list_ports.comports():
        if p.vid == 0x0D28 and p.pid == 0x0204:
            return p.device
    return None


def parse_schedule(text):
    out = []
    for item in text.split(";"):
        item = item.strip()
        if not item:
            continue
        at, _, cmd = item.partition(":")
        try:
            at = float(at)
        except ValueError:
            continue
        if cmd.strip():
            out.append((at, cmd.strip()))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description="Sonar Sentinel serial probe")
    ap.add_argument("port", nargs="?", help="serial port (default: auto-detect micro:bit)")
    ap.add_argument("seconds", nargs="?", type=float, default=12.0, help="duration (default 12)")
    ap.add_argument("--send", default="1:i", help='scheduled commands, e.g. "2:i;6:p;9:s"')
    ap.add_argument("--quiet", action="store_true", help="only print the summary")
    args = ap.parse_args()

    port = args.port or find_port()
    if not port:
        sys.exit("No micro:bit serial port found (VID_0D28&PID_0204). Pass one explicitly.")

    try:
        ser = serial.Serial(port, 115200, timeout=0.2)
    except Exception as exc:
        sys.exit("Cannot open %s: %s\nIs the browser page or a bridge holding the port?" % (port, exc))

    schedule = parse_schedule(args.send)
    samples = []
    alarms = []
    sys_lines = []
    ready = None
    sent = set()
    buf = ""
    t0 = time.time()
    next_tick = 1.0

    print("port %s   %.0fs   commands: %s" % (port, args.seconds, args.send))
    try:
        while time.time() - t0 < args.seconds:
            now = time.time() - t0
            for idx, (at, cmd) in enumerate(schedule):
                if now >= at and idx not in sent:
                    ser.write((cmd + "\n").encode("ascii"))
                    sent.add(idx)

            data = ser.read(512)
            if data:
                buf += data.decode("ascii", "replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    match = A_RE.match(line)
                    if match:
                        samples.append((int(match.group(1)), int(match.group(2))))
                    elif line.startswith("ALARM:"):
                        alarms.append(int(line[6:]))
                    elif line.startswith("SYS:"):
                        sys_lines.append(line)
                        if "READY" in line:
                            ready = line
                    elif not args.quiet and line.startswith("ACK:"):
                        print("  %5.1fs  <- %s" % (now, line))

            if not args.quiet and now >= next_tick:
                next_tick += 1.0
                last = samples[-1] if samples else ("-", "-")
                print("  %5.1fs  samples=%4d  last=A:%s,D:%s" % (now, len(samples), last[0], last[1]))
    finally:
        ser.close()

    elapsed = max(0.001, time.time() - t0)
    angles = [a for a, _ in samples]
    dists = [d for _, d in samples]
    echoes = [d for d in dists if d > 0]

    dirs = []
    for i in range(1, len(angles)):
        delta = angles[i] - angles[i - 1]
        if delta:
            dirs.append(1 if delta > 0 else -1)
    reversals = sum(1 for i in range(1, len(dirs)) if dirs[i] != dirs[i - 1])

    rate = len(samples) / elapsed

    print("\n--- summary ---")
    print("ready line      : %s" % (ready or "MISSING"))
    print("samples         : %d  (%.1f/s)" % (len(samples), rate))
    if samples:
        print("angles          : %d..%d  reversals=%d" % (min(angles), max(angles), reversals))
        print("distance cm     : min=%d median=%d max=%d  echoes>0=%d"
              % (min(dists), statistics.median(dists), max(dists), len(echoes)))
    print("alarm edges     : %s" % (" ".join(str(a) for a in alarms) if alarms else "none"))

    checks = [
        ("handshake", ready is not None),
        ("PCA=OK", bool(ready and "PCA=OK" in ready)),
        ("rate >= 8/s", rate >= 8.0),
        ("angles within 15..165", bool(samples) and all(15 <= a <= 165 for a in angles)),
        ("sweep reverses", reversals >= 1),
    ]
    print()
    ok = True
    for name, passed in checks:
        print("  [%s] %s" % ("PASS" if passed else "FAIL", name))
        ok = ok and passed

    if not echoes:
        print("\n  NOTE: every reading is 0 (no echo). Put a hand or a box 10-40 cm")
        print("        in front of the sensor, and check the RobotBit battery + power")
        print("        switch (USB alone powers only the micro:bit) and that P1=TRIG,")
        print("        P2=ECHO are not swapped.")
    elif ok:
        print("\n  Echoes seen: the sensor is ranging.")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
