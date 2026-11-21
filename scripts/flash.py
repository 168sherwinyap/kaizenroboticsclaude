#!/usr/bin/env python3
"""Copy a .hex onto the mounted MICROBIT volume to flash the board (cross-platform).

Replaces the old ``cmd /c copy /b ... D:\\MICROBIT.HEX`` step. The board appears
as a drive labelled MICROBIT: /Volumes/MICROBIT on macOS, /media/<user>/MICROBIT
on Linux, a MICROBIT-labelled drive on Windows.

Run:  python scripts/flash.py <path-to.hex>
"""

import argparse
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import microbit_util


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hexfile", help="path to the .hex to flash (e.g. sentinel/built/binary.hex)")
    args = ap.parse_args()

    if not os.path.isfile(args.hexfile):
        sys.exit("No such file: %s" % args.hexfile)

    vol = microbit_util.find_microbit_volume()
    if not vol:
        sys.exit("No MICROBIT volume mounted. Plug the board in (it appears as a "
                 "drive labelled MICROBIT) and try again.")

    dest = os.path.join(vol, os.path.basename(args.hexfile))
    print("Copying %s -> %s" % (args.hexfile, dest), flush=True)
    shutil.copyfile(args.hexfile, dest)
    print("Done. The drive vanishes and returns as the board flashes.", flush=True)

    # DAPLink keeps FAIL.TXT on the drive when a copy fails; a successful copy
    # unmounts the drive, so this is a best-effort warning.
    time.sleep(3)
    fail = os.path.join(vol, "FAIL.TXT")
    if os.path.exists(fail):
        sys.exit("FAIL.TXT appeared - the copy failed. Run again to retry.")


if __name__ == "__main__":
    main()
