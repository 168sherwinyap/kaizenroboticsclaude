"""Send every letter/number typed on this PC to the micro:bit over Bluetooth LE.

The board runs the MakeCode program in ble/main.ts, which exposes the Nordic
UART service (NUS). This script scans for "BBC micro:bit", connects, and writes
one "<character>\n" line per key press, which the board scrolls on its display.

With Ctrl held, K/J/R/X are sent as commands instead ("!k", "!j", "!r", "!x"):
happy/sad/circle/cross on the display plus the S1 servo move.

Run:  python ble_keyboard_bridge.py [--name PREFIX] [--debug]
Stop: Ctrl+C
"""

import argparse
import asyncio
import queue
import sys
import threading

from bleak import BleakClient, BleakScanner

try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None

NUS_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
# The micro:bit DAL exposes the NUS characteristic roles swapped from the
# Nordic convention: ...0003 is the writable one (PC -> board), ...0002 carries
# the board's echoes back.
NUS_RX_CHAR = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_CHAR = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

SEND_TIMEOUT = 30.0           # seconds to wait for a board to appear

KEY_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
COMMAND_KEYS = "KJRX"         # these become servo commands when Ctrl is held


def poll_keyboard(out_queue, stop_event, debug=False):
    """Global key listener via pynput (works on Windows/macOS/Linux).

    Ctrl+K/J/R/X sends a "!k"/"!j"/"!r"/"!x" command (faces + servo); the same
    letters without Ctrl are mirrored as ordinary characters.
    """
    if pynput_keyboard is None:
        print("pynput is required for keyboard capture: pip install pynput", flush=True)
        return

    ctrl_down = False
    held = set()
    lock = threading.Lock()

    def on_press(key):
        nonlocal ctrl_down
        if key in (pynput_keyboard.Key.ctrl, pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
            ctrl_down = True
            return
        try:
            ch = key.char
        except AttributeError:
            return
        if not ch:
            return
        ch = ch.upper()
        if ch not in KEY_CHARS:
            return
        with lock:
            if ch in held:
                return  # OS auto-repeat: already sent on the key-down edge
            held.add(ch)
        if ctrl_down and ch in COMMAND_KEYS:
            out_queue.put("!" + ch.lower())
            if debug:
                print("command !%s" % ch.lower(), flush=True)
        else:
            out_queue.put(ch)
            if debug:
                print("key %s" % ch, flush=True)

    def on_release(key):
        nonlocal ctrl_down
        if key in (pynput_keyboard.Key.ctrl, pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
            ctrl_down = False
            return
        try:
            ch = key.char
        except AttributeError:
            return
        if ch:
            with lock:
                held.discard(ch.upper())

    try:
        with pynput_keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            stop_event.wait()
    except Exception as exc:
        print("keyboard listener failed: %s (on macOS grant Accessibility permission)" % exc,
              flush=True)


async def find_board(name_prefix, timeout):
    print("Scanning for a micro:bit over Bluetooth...", flush=True)

    def matches(device, advertisement):
        name = advertisement.local_name or device.name or ""
        if name.startswith(name_prefix):
            return True
        return NUS_SERVICE in [uuid.lower() for uuid in advertisement.service_uuids]

    return await BleakScanner.find_device_by_filter(matches, timeout=timeout)


def on_board_message(_, data):
    """The board echoes "ACK:<char>" for everything it received and displayed."""
    text = bytes(data).decode("ascii", "replace").strip()
    print("board: %s" % text, flush=True)


async def send_char(client, char):
    await client.write_gatt_char(NUS_RX_CHAR, (char + "\n").encode(), response=True)


async def pump(client, key_queue, debug):
    """Write queued characters to the board while the link stays up."""
    while client.is_connected:
        try:
            char = key_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.01)
            continue
        try:
            await send_char(client, char)
            if debug:
                print("sent %s" % char, flush=True)
        except Exception as exc:                      # link dropped mid-write
            print("write failed (%s), reconnecting" % exc, flush=True)
            return


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="BBC micro:bit", help="advertised name prefix")
    parser.add_argument("--address", default=None,
                        help="connect to this BLE address directly instead of scanning")
    parser.add_argument("--debug", action="store_true", help="log every key and write")
    args = parser.parse_args()

    key_queue = queue.Queue()
    stop_event = threading.Event()
    threading.Thread(target=poll_keyboard, args=(key_queue, stop_event, args.debug), daemon=True).start()

    print("Keyboard bridge running - press letters or numbers. Ctrl+C to stop.", flush=True)
    try:
        while True:
            if args.address:
                target = args.address
                print("Connecting to %s..." % target, flush=True)
            else:
                target = await find_board(args.name, SEND_TIMEOUT)
                if target is None:
                    print("No micro:bit found. Put it in pairing mode: hold A+B, tap reset, "
                          "wait for 'PAIRING MODE!'.", flush=True)
                    continue
                print("Connecting to %s (%s)..." % (target.name, target.address), flush=True)

            try:
                async with BleakClient(target, timeout=20.0) as client:
                    print("Connected. Typing now mirrors on the board.", flush=True)
                    key_queue.queue.clear()      # drop keys pressed while offline
                    try:
                        await client.start_notify(NUS_TX_CHAR, on_board_message)
                    except Exception as exc:
                        print("(could not subscribe to board echoes: %s)" % exc, flush=True)
                    try:
                        await pump(client, key_queue, args.debug)
                    except Exception as exc:
                        if "auth" not in str(exc).lower() and "encrypt" not in str(exc).lower():
                            raise
                        print("Board wants pairing; asking the host to pair...", flush=True)
                        await client.pair()
                        print("Paired. Retrying.", flush=True)
                        await pump(client, key_queue, args.debug)
            except Exception as exc:
                print("Connection problem: %s" % exc, flush=True)
            print("Disconnected; searching again...", flush=True)
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        print("\nStopped.", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
