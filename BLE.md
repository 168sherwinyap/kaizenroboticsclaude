# Running the Bluetooth keyboard mirror without Claude Code

Two pieces:

| Piece | Where it lives | When it runs |
|---|---|---|
| Board program | flashed onto the micro:bit | starts by itself when the board powers up |
| PC bridge | `ble_keyboard_bridge.py` | you start it; it must be running to send keys |

Nothing needs to be rebuilt or reflashed for normal use.

## Start it

1. Double-click **`run_ble_bridge.cmd`** (Windows) or run **`./run_ble_bridge.sh`**
   (macOS/Linux).
   A console window opens, saying `Keyboard bridge running`.
2. **Tap the micro:bit's reset button once.**
   The program starts and advertises for only a few seconds; the bridge, already
   scanning, catches it. Start the bridge *before* the reset or it will miss the window.
3. When the window says `Connected. Typing now mirrors on the board.`, type normally.

Stop it with **Ctrl+C** in that window (or close the window).

Command-line equivalent:

```
python ble_keyboard_bridge.py --debug
```

`--debug` prints every key and every board echo as it happens.

## Keys

- Any letter or digit: scrolls on the micro:bit, echoed as `ACK:<char>`.
- **Ctrl+K** happy face + servo 90°, **Ctrl+J** sad + 0°, **Ctrl+R** circle + 0°,
  **Ctrl+X** X + 180°. Echoes `smile` / `frown` / `circle` / `cross`.
- Plain k/j/r/x are just letters.
- No PC at all: **A** = Ctrl+K, **B** = Ctrl+X, for demoing the servo standalone.

The servo needs the RobotBit battery connected and its power switch ON. Faces and
Bluetooth work without it.

## If it will not connect

- Board on and powered? Bridge window open before you reset the board?
- Tap reset once more with the bridge already running.
- Servo limp but faces working: RobotBit battery / power switch.

## Pairing (only needed after a reflash, or if you remove the device)

The board and your computer keep a bond. Reflashing the firmware wipes the board's side,
so the two disagree and every connection drops after about a second.

1. Put the board in pairing mode: hold **A+B**, tap reset, keep holding A+B until
   `PAIRING MODE!` scrolls (it then shows a pattern).
2. Pair it from the OS: **Settings → Bluetooth** (Windows: *Add device → Bluetooth*;
   macOS: *Bluetooth*; Linux: `bluetoothctl pair <MAC>`), pick `BBC micro:bit [xxxxx]`.
3. Start the bridge, then tap reset once.

If pairing misbehaves, remove `BBC micro:bit` from the OS's Bluetooth list first, then
repeat. `python scripts/ble_pair_then_grab.py` automates unpair → pair on sight on
Windows (on macOS/Linux remove the device manually first).

## Rebuilding the firmware (rarely needed)

```
cd ble
makecode
```

Then flash it: `python scripts/flash.py ble/built/binary.hex` (or copy the file to the
MICROBIT drive). After that, re-pair as above. Building needs Node.js and
`npm install -g makecode`.

## Going back to MicroPython

Run `python scripts/flash.py firmware/micropython-microbit-v2.1.1.hex`, then
`python scripts/install_servo.py` — that restores the original faces + servo over USB
serial, and the Bluetooth program is gone.
