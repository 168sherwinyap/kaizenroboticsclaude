"""Cross-platform helpers for finding the micro:bit on the host PC.

The micro:bit enumerates as a DAPLink USB device (VID 0x0D28 / PID 0x0204):

- its USB serial port is what the bridges and probes open, and
- its filesystem mounts as a volume labelled "MICROBIT" that you copy a `.hex`
  onto to flash the board.

These two functions hide the OS-specific names (``COMx`` vs ``/dev/tty*``, and
``D:`` vs ``/Volumes/MICROBIT``) behind one call each.
"""

import os
import sys

try:
    from serial.tools import list_ports
except ImportError:
    list_ports = None

MICROBIT_VID = 0x0D28
MICROBIT_PID = 0x0204


def find_serial_port():
    """Return the micro:bit USB serial port device string, or None if absent."""
    if list_ports is None:
        return None
    for p in list_ports.comports():
        if p.vid == MICROBIT_VID and p.pid == MICROBIT_PID:
            return p.device
    return None


def find_microbit_volume():
    """Return the path of the mounted MICROBIT volume, or None if absent."""
    if sys.platform == "win32":
        # The micro:bit drive is labelled MICROBIT and carries MICROBIT.HTM at
        # its root. Iterate drive letters rather than relying on the label, so
        # it works even when Windows renames the drive.
        import string
        for letter in string.ascii_uppercase:
            root = letter + ":\\"
            if os.path.exists(root) and os.path.isfile(os.path.join(root, "MICROBIT.HTM")):
                return root
        return None

    if sys.platform == "darwin":
        candidate = "/Volumes/MICROBIT"
        return candidate if os.path.isdir(candidate) else None

    # Linux: udisks2 mounts removable media under /media/<user>/ or
    # /run/media/<user>/.
    user = os.environ.get("USER") or os.environ.get("USERNAME") or ""
    for base in ("/media/" + user, "/run/media/" + user, "/media"):
        candidate = os.path.join(base, "MICROBIT")
        if os.path.isdir(candidate):
            return candidate
    return None
