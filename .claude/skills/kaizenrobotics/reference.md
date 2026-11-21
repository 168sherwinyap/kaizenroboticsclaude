# Reference: every program in this repository

Detail for each board program and its PC side: hardware facts, architecture, commands,
install and verify steps, protocols and file lists. `SKILL.md` in this folder has the
stack choice, the hard constraints and the troubleshooting table. All paths are relative
to the repository root. Commands work on Windows, macOS and Linux; the serial port is
auto-detected by VID/PID and the micro:bit mounts as a drive labelled `MICROBIT`
(`/Volumes/MICROBIT` on macOS, `/media/<user>/MICROBIT` on Linux, a `MICROBIT` drive on
Windows).

## Hardware/firmware facts (verified on this device)

- Firmware: micro:bit Foundation MicroPython v2.1.1 (MicroPython 1.18 core), flashed
  from `firmware/micropython-microbit-v2.1.1.hex`.
- Stock firmware has **no `robotbit` module**; `machine` exists but has no `Pin`,
  `I2C`, or `PWM`; the `compile` builtin is absent.
- RobotBit servo ports **S1–S8 are not micro:bit GPIO**. They are outputs of an onboard
  **PCA9685** I²C PWM driver at address **0x40**: S1 = channel 8, S2–S8 = 9–15,
  motors = channels 0–7. Channel register base is `0x06 + 4*channel` (`S1 = 0x26`,
  `S2 = 0x2A`, … `S5 = 0x36`). `sentinel/main.ts` drives S1+S2 and `handlab/main.ts`
  drives S1–S5 through the same parameterised `writeChannel`. I²C is on P19/P20 at 100 kHz.
- Servo pulses are 600–2400 µs; PCA9685 prescale **121** gives 50 Hz. The prescale
  resets whenever the RobotBit loses power, so `main.py` re-initialises the chip before
  every move.
- The servo rail is powered from the RobotBit's 18650 battery with its power switch ON.
  USB alone powers only the micro:bit. The RobotBit's own USB port is charge-only;
  program through the micro:bit's USB port.
- The `MICROBIT` drive is DAPLink storage, **not** the MicroPython filesystem. Copying
  `main.py` to it does not install or run it — the board's `os.listdir()` stays empty.
  Dropping a `.hex` on it does flash it (takes ~20 s; a first attempt can fail with
  `FAIL.TXT` / "transfer timed out" — retry the copy).
- The micro:bit's USB CDC port is identified by USB VID `0D28` / PID `0204`; it renumbers
  on a re-plug **or a power cycle**, so always re-detect. The bridges, probes and
  `flash.py` auto-detect it (`COMx` on Windows, `/dev/tty.usbmodem*` on macOS,
  `/dev/ttyACM*` on Linux); the Sentinel page's **Connect** picker lists whatever exists.
  Several older scripts in `scripts/archive/` hardcode COM6 or COM7 — pass the port
  explicitly when running those.
- **v2 compass gotcha (verified):** `input.compassHeading()` and `input.calibrateCompass()`
  hang the board at boot on this hardware — the program never runs, even a first serial
  write at module scope is lost. `input.magneticForce()` (raw µT) works fine. Read the raw
  magnetometer and derive heading client-side instead (`handlab/` does this). Also: a
  module-scope `serial.writeLine` can be dropped before the USB CDC is ready; put output in
  the main loop (or after a ~500 ms `basic.pause`).

## Architecture

Three pieces form the whole system:

1. **`keyboard_bridge.py`** (PC side). Globally listens (via `pynput`) for K, J, R
   and X, writes one byte per key press to the serial port at 115200, and prints whatever
   the board echoes. Auto-detects the port, sends on key-down edges only, stops with
   Ctrl+C. It holds the serial port exclusively while running.
2. **`main.py`** (board side). Loops on `uart.any()` / `uart.read(1)`: `k` shows
   `Image.HAPPY`, prints `smile`, then drives S1 to 90°; `j` shows `Image.SAD`, prints
   `frown`, then drives S1 to 0°; `r` shows the `CIRCLE` image, prints `circle`, then
   drives S1 to 0°; `x` shows the `CROSS` image, prints `cross`, then drives S1 to 180°.
   It contains a small inline PCA9685 driver (`_wr` / `_init` / `servo`). I²C errors are
   swallowed so the images keep working if the RobotBit is off.
3. **`run_bridge.sh`** / **`run_bridge.cmd`**. Launcher for the bridge.

The serial protocol is the contract: the bridge sends raw `k`/`j`/`r`/`x` and prints the
board's echo verbatim. Keep the `smile` / `frown` / `circle` / `cross` echo strings
unless the bridge changes too. The bridge's `-SmileKey` / `-FrownKey` / `-CircleKey` /
`-CrossKey` parameters let tests remap the keys (F13/F14 for the smile/frown test).

`main.py` is the single source of truth for the board program. `scripts/archive/install_kj.ps1`
embeds an older copy of the program and is legacy — edit `main.py` instead.

## Common commands

Run these from the repository root. Every path below is relative to it.

Run the keyboard bridge (or double-click `run_bridge.cmd` / run `./run_bridge.sh`):

```bash
python keyboard_bridge.py
```

Install the current `main.py` onto the board (auto-detects the port; `--port <port>` to
override):

```bash
python scripts/install_servo.py
```

Verify faces and servo PWM values on hardware:

```bash
python scripts/verify_servo.py
```

Find the micro:bit's serial port:

```bash
python -c "from scripts.microbit_util import find_serial_port; print(find_serial_port())"
# or: ls /dev/tty.usbmodem* (macOS) / ls /dev/ttyACM* (Linux) / Get-PnpDevice (Windows)
```

Stop a stray bridge that is holding the port (install/verify fail with an "access denied"
error while one runs):

```bash
pkill -f keyboard_bridge        # macOS/Linux
# Windows: taskkill /F /IM python.exe   (or close the bridge window)
```

Flash a `.hex` onto the board:

```bash
python scripts/flash.py firmware/micropython-microbit-v2.1.1.hex
```

Then wait for the MICROBIT volume to vanish and return; retry if `FAIL.TXT` appears.
After flashing, the board runs MicroPython but has an empty filesystem (no `main.py`)
until an installer runs.

## Installing a program (the tricky part)

`scripts/install_servo.py` is the canonical upload path: open the port, send Ctrl-C to
break into the REPL, Ctrl-E for paste mode, send a wrapper that writes `main.py` from
disk line by line, Ctrl-D to execute it, check `FILES`/`LEN`, then Ctrl-D to soft-reset
into the new program. Constraints this imposes:

- `main.py` must be pure ASCII and must not contain `'''` (the installer wraps it in
  `r'''...'''`; CRLF is normalised).
- Paste-mode lines are limited to 256 characters; keep even the longest line well under.
- The board filesystem is ~30 KB; `main.py` is ~1.3 KB.
- A soft reset re-enumerates USB — wait ~3 s before sending serial data.
- Ctrl-C interrupts the running program and leaves its globals at the REPL; Ctrl-D soft-
  resets and runs `main.py`.
- The bridge must be stopped before installing or verifying (exclusive port access).

## Verification

`scripts/verify_servo.py` presses the keys over serial and reads state back. Expected
values from a healthy setup:

| Check | Expected |
|---|---|
| `i2c.scan()` | contains `64` (0x40 PCA9685) |
| PRESCALE (0xFE) | `121` |
| channel-8 OFF after `k` | `307` (1500 µs, 90°) |
| channel-8 OFF after `j` | `123` (600 µs, 0°) |
| channel-8 OFF after `r` | `123` (600 µs, 0°) |
| channel-8 OFF after `x` | `492` (2400 µs, 180°) |
| display pixels after `k` | `(0,3)=9, (0,4)=0` (happy) |
| display pixels after `j` | `(0,3)=0, (0,4)=9` (sad) |
| display pixels after `r` | `(0,1)=9, (2,2)=0, (2,0)=9` (circle) |
| display pixels after `x` | `(0,1)=0, (2,2)=9, (2,0)=0` (X) |
| serial echo | `smile` / `frown` / `circle` / `cross` |

The physical servo swing is the one thing scripts cannot check. If registers are correct
but nothing moves, check the RobotBit battery and power switch. 600 µs (0°) sits at the
edge of the hobby-servo range; raise the minimum pulse to ~700 µs if it buzzes or strains.

## Bluetooth keyboard mirror

This program is a **MakeCode** build, not MicroPython: micro:bit MicroPython
has no BLE stack (`import bluetooth` / `ubluetooth` both fail, and `dir(microbit)` has
no Bluetooth API), so Bluetooth is impossible on that firmware.

- `ble/main.ts` — board program. `bluetooth.startUartService()`, then for every
  received `<char>\n`: `!k`/`!j`/`!r`/`!x` are the servo commands (HAPPY+S1 90°,
  SAD+S1 0°, CIRCLE+S1 0°, CROSS+S1 180°), echoing `smile` / `frown` / `circle` /
  `cross`; every other character scrolls and echoes `ACK:<char>`. The `!` prefix is
  added by the PC bridge only when **Ctrl** is held, so plain typing of k/j/r/x just
  mirrors the letter. Logs `BOOT` / `CONNECTED` / `DISCONNECTED` / `GOT:` / `SERVO:` /
  `BUTTON:` on the USB serial port.
  - Servo: the same inline PCA9685 driver as `main.py`, but through
    `pins.i2cWriteBuffer(0x40, ...)` (there is no `i2cWriteBuffer` block, but the shim
    exists). Moves run in `control.inBackground` so a stuck I2C bus cannot block BLE.
  - Do **not** call the servo from the boot path: doing so wedged the whole program
    (BOOT printed, then no BLE). It now only runs on a key press or button.
  - Local self-test with no PC: **A** = the `k` command, **B** = the `x` command.
    Verified on hardware: faces and the S1 swing both work from the buttons.
- `ble/pxt.json` — declares `bluetooth`; it conflicts with the default `radio`
  package (`microbit-dal.bluetooth.enabled`), so `radio` must stay out.
- Build: `cd ble && makecode` (CLI via `npm install -g makecode`) → `ble/built/binary.hex`,
  flashed with `python scripts/flash.py ble/built/binary.hex`. `ble/mkc.json` pins the **stable** editor
  (`https://makecode.microbit.org/`); the beta target's Bluetooth never delivered UART
  data. The trailing slash matters — without it mkc builds a broken `ENOTFOUND` URL.
- `ble_keyboard_bridge.py` — PC side (Python + `bleak`). Listens globally (via `pynput`)
  for A–Z/0–9, connects to `BBC micro:bit`, writes one `<char>\n` per key press, prints
  the board's echoes. While Ctrl is down, K/J/R/X are sent as `!k`/`!j`/`!r`/`!x`
  commands instead of letters. Run `python ble_keyboard_bridge.py [--debug]` or
  `run_ble_bridge.sh` / `run_ble_bridge.cmd`.

Working procedure (verified end to end):

1. Start the bridge first — it scans continuously and reconnects by itself:
   `python ble_keyboard_bridge.py` (or `run_ble_bridge.sh` / `run_ble_bridge.cmd`).
2. If the board has no bond (e.g. after any reflash), pair it: A+B + reset until
   "PAIRING MODE!", then `python scripts/ble_pair_then_grab.py`.
3. **Tap reset once** with the bridge running. The program starts and advertises
   briefly; the running bridge catches it and connects. That reset-with-bridge-running
   step is what makes the short advertising window usable — started after the board is
   already up, the bridge will usually miss it.
4. Type: letters/digits scroll and echo `ACK:<char>`; Ctrl+K/J/R/X run the servo
   commands and echo `smile` / `frown` / `circle` / `cross`.

Pairing/connection constraints (learned the hard way):

- The board only advertises **reliably** in pairing mode: hold A+B, tap reset, wait for
  "PAIRING MODE!" / "BBC micro:bit [xxxxx]". A short reset afterwards leaves pairing
  mode and starts the program.
- Flashing a new hex wipes the Bluetooth bond → pair again afterwards.
- On this board/PC the program-mode advertising window is short and unreliable: after
  pairing (or a full power cycle) the board is reachable for a brief window, then scans
  return nothing and connect-by-address fails. Connect promptly after pairing/reset; if
  it is missed, go back to pairing mode. This is why the k/j/r/x servo path was verified
  with the A/B buttons rather than over BLE.
- The RobotBit battery keeps the micro:bit powered: unplugging USB alone does **not**
  reboot it. A true power cycle needs the RobotBit switch OFF as well.
- Pairing must happen in **pairing mode**. Calling `pair()` while the program advertises
  fails with bleak `Could not pair with device: 19`.
- A stale OS bond makes every connection drop after ~1 s, even before any GATT
  operation. Unpair first (Settings → Bluetooth on Windows/macOS, or
  `bluetoothctl remove <MAC>` on Linux), then pair fresh.
- NUS characteristic roles are swapped from the Nordic convention: write to
  `6E400003-B5A3-F393-E0A9-E50E24DCCA9E`; echoes arrive on `...0002` (indicate).
- Do not enumerate `client.services` and then reuse the client — WinRT raises "The
  object has been closed". Connect, `start_notify`, then write.
- `scripts/archive/probe_ble.py`, `scripts/serial_watch.py` and `scripts/archive/ble_probe_connect.py`
  are the diagnostics used to prove BLE support and UART delivery.

Restore the MicroPython face/servo setup: flash
`firmware/micropython-microbit-v2.1.1.hex` with `python scripts/flash.py`, then run
`scripts/install_servo.py`.

## Flappy Bird hand-control game (HC-SR04 → monitor)

Two pieces: the board reads an **HC-SR04 ultrasonic sensor** and streams the distance over
USB serial; a browser page reads it over the **Web Serial API** and renders Flappy Bird
whose height mirrors the hand's height (raise hand = fly up). S1 flaps as a wing **only
while the bird is moving up**.

**Wiring** (HC-SR04 → micro:bit edge pins, not S1–S8):

| HC-SR04 | Connect to |
|---|---|
| VCC | **5 V rail** (next to the servo ports) — not 3.3 V |
| GND | GND |
| TRIG | **P1** |
| ECHO | **P2 through a divider**: 1 kΩ ECHO→P2, 2 kΩ P2→GND (5 V → ~3.3 V) |

ECHO is 5 V and micro:bit pins are 3.3 V (not 5 V tolerant), hence the divider. Powering
the module at 3.3 V instead is electrically safe but many HC-SR04 clones read 0 / are
flaky there. Avoid P0 (buzzer), P16 (RGB LEDs), P19/P20 (I²C to the PCA9685).

- `flappy/main.ts` — board program (MakeCode). `pins.pulseIn` reads the HC-SR04 (TRIG=P1,
  ECHO=P2); `basic.forever` writes `D:<cm>` over USB serial ~20×/s; `serial.onDataReceived`
  flaps the S1 wing on a `f` line; button A flaps once as a local self-test. Same inline
  PCA9685 driver as `ble/main.ts` (0x40, prescale 121, S1 = channel 8), moves in
  `control.inBackground`. Build `cd flappy && makecode` → `flappy/built/binary.hex`, flash
  by copying to `D:`. `flappy/pxt.json` declares `core` only (no `bluetooth`, no `radio`);
  `flappy/mkc.json` copies `ble/mkc.json` (trailing slash matters).
- `flappy/web/index.html` + `flappy/web/game.js` — the browser game. Chrome/Edge only; Web Serial needs
  a secure context, so it is served on `localhost` (never `file://`). `game.js` parses
  `D:<cm>` lines, maps distance → bird Y, and writes `f\n` when the bird moves up.
  `run_flappy.sh` / `run_flappy.cmd` serves `flappy/web/` on `:8000` and opens the URL; click
  **Connect** and pick the micro:bit port.
- `run_flappy.sh` / `run_flappy.cmd` — launcher.
- `kaizen-pushup/` — pushup counter (`index.html` + `app.js`, own README). It needs no
  board program of its own: it reads the same `D:<cm>` stream from the Flappy build. Sensor
  on the floor pointed up at the chest; down < 2 in, up > 5 in (and < 1.5 m); a rep is
  down → up. `kaizen-pushup/run_kaizen_pushup.sh` / `run_kaizen_pushup.cmd` serves it on `:8001`.

Protocol (the contract): board → browser `D:<cm>` lines; browser → board `f\n` (flap).

Sensor robustness lives in `flappy/web/game.js`, not the board: readings `<= 0` or `> MAX_VALID_CM`
(default 40 cm) are treated as "hand gone / spurious echo" and **hold** the bird rather
than snapping it to the top (a bare HC-SR04 emits spurious far echoes when the hand leaves
its beam); a median-of-`DIST_SAMPLES` (3) filter drops single-sample spikes. Tunables at the
top of `game.js`: `NEAR_CM`/`FAR_CM` (distance→height), `MAX_VALID_CM`, `DIST_SAMPLES`,
`PIPE_SPEED`, `PIPE_GAP`, `SMOOTH`. Press **D** in the game for an on-screen raw readout.

Web Serial opens the serial port **exclusively**: `serial_watch.py` / the MicroPython
bridge fail with an "access denied" error while the browser is connected (and vice-versa).

## Sonar Sentinel — dual-servo radar + guard arm

A single self-contained demo folder: `sentinel/` holds the MakeCode board program, its
build output, the browser app and a README. S1 pans an HC-SR04 through a 20°–160° sweep;
S2 is a guard arm that locks when something stays inside a keep-out distance; the browser
draws a live phosphor radar scope with fading blips, a real sweep line, a draggable
keep-out ring and an animated arm, and pings on the alarm edge. Verified end to end on
this board: `SYS:READY,PCA=OK`, a steady `A:` stream with reversals, `ALARM:1/0` edges,
both servos moving, and live blips in the page. The board renumbers its serial port after a
power cycle — reconnect through the page's picker, don't assume a fixed COM number.

**Wiring**: the HC-SR04 table above is unchanged (VCC 5 V rail, TRIG P1, ECHO P2 through
the 1 kΩ/2 kΩ divider). Mount the sensor on the **S1 horn**; put the guard arm on **S2**.
The RobotBit battery and power switch must be ON for the servos, and the HC-SR04 VCC is on
that same 5 V rail — with USB only, `PCA=OK` can still appear (I²C is 3.3 V) while the
sensor and servos stay dead.

- `sentinel/main.ts` — board program. One `basic.forever` fiber owns **all** I²C and the
  display; the serial handler and buttons only set globals. `pcaInit()` runs at the start
  of each sweep pass, then reads PRESCALE back to report `PCA=OK|ERR`. `sweepStep()` moves
  S1, waits `SETTLE_MS` (45 ms), pings, emits `A:<deg>,D:<cm>`, and calls `endSweep()`
  (`N:<cm>`) at each turnaround. The alarm latches on any sample inside `keepOutCm` and
  releases `ALARM_HOLD_MS` (2.6 s, over one sweep) after the last threat, so a hand
  anywhere in the field keeps S2 closed. Button A pauses/resumes, B wiggles both servos.
- `sentinel/web/index.html` + `app.js` — radar scope, keep-out ring, guard-arm SVG, event
  log, Web Audio ping. Demo mode runs a synthetic sweep whenever no board is connected
  (and again after a disconnect), so the UI is alive without hardware. `app.js` fixes the
  flappy app's connection bugs: feature-detects Web Serial, re-enables Connect after a
  disconnect, releases the reader/writer, and handles partial lines.
- `run_sentinel.sh` / `run_sentinel.cmd` — serves `sentinel/web` on **:8002** (localhost) and opens it.
- `scripts/radar_probe.py` — serial protocol oracle: parses the stream, counts rate and
  reversals, schedules commands (`--send "2:i;6:p;9:s"`), prints PASS/FAIL. Close the
  browser first; Web Serial owns the port exclusively.
- `sentinel/README.md` — operator how-to, protocol table and troubleshooting.

Protocol (the contract, newline delimited):

```
board ->  A:<deg>,D:<cm>   N:<cm>   ALARM:<0|1>   K:<cm>   ACK:<cmd>
          SYS:READY,PCA=OK|ERR,ALARM=0|1     SYS:SWEEP|PAUSED|PARK|TEST
browser -> t:<cm>   s   p   c   w   i   d
```

`d` is a sensor diagnostic: it triggers once with a 100 ms pulse window and prints
`DIAG:US=<raw echo microseconds>`. A live HC-SR04 with no target holds ECHO high ~38 ms
(≈38000); `DIAG:US=0` means the module is unpowered, ungrounded, or miswired.

Build, flash, run:

```bash
cd sentinel && makecode
```

```bash
python scripts/flash.py sentinel/built/binary.hex
```

```bash
./run_sentinel.sh   # or run_sentinel.cmd on Windows
```

Verify without a browser (12 s, auto-detects the port):

```bash
python scripts/radar_probe.py 12
```

Expected: `SYS:READY,PCA=OK`, ~9–20 `A:` samples/s with angles 20..160 and reversals
about every 2 s, and `N:` at each turnaround. `PCA=ERR` means the PCA9685 did not answer
the prescale read-back — RobotBit off/unseated. Restore Flappy with
`flappy/built/binary.hex`; restore MicroPython per the section above.

## HandLab — v2 sensor dashboard + 5-servo hand

`handlab/` streams every v2 sensor (temperature, light, microphone, 3-axis accelerometer,
3-axis magnetometer) plus the HC-SR04 sonar distance to a browser over Web Serial, and the
same page drives five servos as a hand. It was built for a **second** micro:bit + RobotBit,
independent of the Sentinel board.

**Wiring**: five servos on **S1–S5** = PCA9685 channels **8–12** (`0x26`–`0x36`), mapped
Thumb/Index/Middle/Ring/Pinky. HC-SR04 wiring as in the Flappy section (5 V rail, TRIG=P1,
ECHO=P2 through the divider). Battery + power switch ON for the servo rail.

- `handlab/main.ts` — board firmware. One `basic.forever` fiber owns **all** I²C and the
  display; the serial handler and buttons only set globals. A parameterised
  `writeChannel(ch, deg)` drives the five servos; one telemetry line streams every ~100 ms.
  Servos home to **0°** (`HOME = 0`), slider range 0–180°. The `home` command returns all
  five to 0° (Button B too); Button A cycles the LED-matrix readout. Moves are staggered
  one channel per ~15 ms tick so five servos never snap off one rail at once.
- `handlab/web/index.html` + `app.js` — the dashboard. Sensor tiles with sparklines
  (temp/light/mic/sonar), a **3D micro:bit model** (a 5×4×0.3 cm prism) that tilts with
  the accelerometer in its **standing** pose (Y up), a **compass** with a smoothed needle,
  five finger sliders, and **Home** / **Compass North Reset** buttons. There are **no
  preset poses** — moving all five servos at once reset the RobotBit (power surge). Demo
  mode feeds synthetic standing-pose data when no board is connected.
- `run_handlab.sh` / `run_handlab.cmd` — serves `handlab/web` on **:8003** (localhost) and opens it.
- `scripts/handlab_probe.py` — serial probe for the telemetry/servo protocol.
- `handlab/README.md` — operator how-to, protocol table, troubleshooting.

Protocol (the contract, newline delimited):

```
board ->  S T=<c> L=<0-255> MIC=<0-255> AX/AY/AZ=<mg> HX/HY/HZ=<uT> D=<cm>
          PCA=OK|ERR   ACK:<cmd>   SERVO <n>=<deg>
browser -> s1:<deg> .. s5:<deg>   home   i
```

**Magnetometer/compass**: `input.compassHeading()` / `input.calibrateCompass()` hang this
board at boot (see the gotcha under Hardware/firmware facts), so the firmware reads only
raw `input.magneticForce()` and the dashboard derives heading client-side with a **Compass
North Reset** re-baseline.

Build, flash, run:

```bash
cd handlab && makecode
```

```bash
python scripts/flash.py handlab/built/binary.hex
```

```bash
./run_handlab.sh   # or run_handlab.cmd on Windows
```

Verify without a browser:

```bash
python scripts/handlab_probe.py 12
```

Expected: `PCA=OK`, ~10 `S T=.. L=.. MIC=..` samples/s, a steady magnetic-field magnitude
(~50–200 µT), and `SERVO n=<deg>` echoes. `AX/AY/AZ` reflect the standing pose
(`AY≈1024`, `AX≈-100`, `AZ≈-20` when standing on its edge).

## Other files

- `scripts/archive/` — bring-up leftovers, kept for reference only. Do not run or copy
  from them without reading them first: many hardcode COM6/COM7, and the installers in
  there embed older copies of the board program.
  - `main_old_board.py` — the previous board program (buttons A/B, logo touch, shake
    gesture). Not deployed.
  - `install_kj.ps1`, `save_v2.ps1`, `save_and_run.ps1` — older installers, superseded by
    `scripts/install_servo.py`.
  - `probe_*.ps1`, `verify_k.ps1`, `verify_v2.ps1`, `verify_running.ps1`, `test_keys.ps1`,
    `serial_check.ps1`, `check_state.ps1`, `finalize.ps1`, `microbit_verify.ps1` — ad-hoc
    hardware probes (UART, logo touch, images, faces).
  - `orchestrate_keytest.ps1` + `send_test_keys.ps1` — tests the bridge by injecting
    synthetic F13/F14 keys (side-effect free) and checking the board's echoes.
  - `probe_ble.py`, `ble_probe_connect.py`, `ble_pair_and_test.py`, `ble_pair_now.py`,
    `ble_test_session.py` — the Bluetooth bring-up probes.
- `*/built/binary.hex` — the flashable build of each MakeCode program. The rest of
  `built/` and any `pxt_modules/` are build output, ignored by git and recreated by
  `makecode`.
- `kaizen-pushup/` — the pushup counter app (browser only, reuses `flappy/built/binary.hex`).
- `kaizen-pushup/run_kaizen_pushup.sh` / `run_kaizen_pushup.cmd` — launcher for the pushup page on `:8001`.
- `sentinel/` — the Sonar Sentinel demo (board program, browser app, README).
- `run_sentinel.sh` / `run_sentinel.cmd` — launcher for the radar page on `:8002`.
- `scripts/radar_probe.py` — serial probe for the radar protocol.
- `handlab/` — the HandLab demo (board program, browser app, README).
- `run_handlab.sh` / `run_handlab.cmd` — launcher for the HandLab page on `:8003`.
- `scripts/handlab_probe.py` — serial probe for the HandLab telemetry/servo protocol.
- `.claude/launch.json` — dev-server entries for the Claude app's browser pane (flappy
  `:8000`, kaizen-pushup `:8001`, sentinel `:8002`, handlab `:8003`).
- `keyboard_bridge.py`, `scripts/install_servo.py`, `scripts/verify_servo.py`,
  `scripts/flash.py`, `scripts/microbit_util.py` — cross-platform PC tools; see
  `requirements.txt` for their Python dependencies.
