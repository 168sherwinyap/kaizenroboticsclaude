#!/usr/bin/env python3
"""Read and exercise the HandLab sensor + servo serial protocol.

Close the browser first — Web Serial owns the serial port exclusively.

Usage:
    python scripts/handlab_probe.py                  # auto-detect, 12 s
    python scripts/handlab_probe.py <port> 20
    python scripts/handlab_probe.py <port> 20 --send "1:i;2:s1:150;4:s5:30;6:home"

Scheduled commands use "<seconds>:<command>" separated by ';'. Commands:
    i            identify (PCA=OK|ERR)   s<n>:<deg>   set servo n (1-5)   home
"""

import argparse
import re
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial is required: pip install pyserial")

SAMPLE_RE = re.compile(
    r"S T=([-\d.]+) L=(\d+) MIC=(\d+) AX=(-?\d+) AY=(-?\d+) AZ=(-?\d+)"
    r" HX=(-?[\d.]+) HY=(-?[\d.]+) HZ=(-?[\d.]+) D=(\d+)")


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
    ap = argparse.ArgumentParser(description="HandLab serial probe")
    ap.add_argument("port", nargs="?", help="serial port (default: auto-detect micro:bit)")
    ap.add_argument("seconds", nargs="?", type=float, default=12.0, help="duration (default 12)")
    ap.add_argument("--send", default="1:i;2:home", help='scheduled commands, e.g. "2:s1:150;5:s5:30"')
    ap.add_argument("--quiet", action="store_true", help="only print the summary")
    args = ap.parse_args()

    port = args.port or find_port()
    if not port:
        sys.exit("No micro:bit serial port found (VID_0D28&PID_0204). Pass one explicitly.")

    try:
        ser = serial.Serial(port, 115200, timeout=0.2)
    except Exception as exc:
        sys.exit("Cannot open %s: %s\nIs the browser page holding the port?" % (port, exc))

    schedule = parse_schedule(args.send)
    samples = []
    servos = []
    pca = None
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
                    m = SAMPLE_RE.match(line)
                    if m:
                        samples.append([float(m.group(i)) for i in range(1, 11)])
                    elif line.startswith("PCA="):
                        pca = line
                    elif line.startswith("SERVO"):
                        servos.append(line)
                    elif not args.quiet and line.startswith("ACK:"):
                        print("  %5.1fs  <- %s" % (now, line))

            if not args.quiet and now >= next_tick:
                next_tick += 1.0
                if samples:
                    s = samples[-1]
                    print("  %5.1fs  T=%s L=%s MIC=%s HX=%s D=%s" %
                          (now, s[0], s[1], s[2], s[6], s[9]))
    finally:
        ser.close()

    elapsed = max(0.001, time.time() - t0)
    rate = len(samples) / elapsed

    print("\n--- summary ---")
    print("PCA line        : %s" % (pca or "MISSING"))
    print("samples         : %d  (%.1f/s)" % (len(samples), rate))
    if samples:
        temps = [s[0] for s in samples]
        mags = [ (s[6] ** 2 + s[7] ** 2 + s[8] ** 2) ** 0.5 for s in samples ]
        dists = [s[9] for s in samples]
        print("temperature C   : %.1f..%.1f" % (min(temps), max(temps)))
        print("magnetic field uT: %.0f..%.0f" % (min(mags), max(mags)))
        print("sonar cm        : %.0f..%.0f  echoes>0=%d" %
              (min(dists), max(dists), sum(1 for d in dists if d > 0)))
    if servos:
        print("servo echoes    : %d (%s ...)" % (len(servos), servos[-1]))

    checks = [
        ("PCA=OK", bool(pca and "OK" in pca)),
        ("rate >= 8/s", rate >= 8.0),
        ("samples seen", len(samples) > 0),
        ("magnetic field plausible", bool(samples) and 20 <= mags[-1] <= 200),
    ]
    print()
    ok = True
    for name, passed in checks:
        print("  [%s] %s" % ("PASS" if passed else "FAIL", name))
        ok = ok and passed

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
