---
name: kaizenrobotics
description: Drive a BBC micro:bit v2 on a KittenBot RobotBit from this PC — display faces, the S1–S5 PCA9685 servos, an HC-SR04 ultrasonic sensor, the v2's accelerometer/magnetometer/mic/light/temperature sensors, USB-serial and Bluetooth LE programs, and browser apps over Web Serial (flappy-bird hand control, Kaizen pushup counter, a dual-servo radar, a 5-servo hand + sensor dashboard), plus building/flashing/verifying firmware and the pairing quirks of each stack. Use when changing key→face/servo behaviour, writing or flashing a board program, mirroring the keyboard over Bluetooth, reading a distance sensor, streaming v2 sensors to a dashboard, building a Web Serial browser app, verifying servo PWM, or debugging a display/servo/BLE/sensor problem.
---

# micro:bit v2 + RobotBit: faces, servo, HC-SR04, USB serial, Bluetooth, Web Serial

Project root: the repository root, the folder that holds `CLAUDE.md` (three levels above
this SKILL.md) — all paths below are relative to it.
Hardware: micro:bit v2.2 on a KittenBot RobotBit 2.2, 180° hobby servos on S1–S5 (S1–S8
available), HC-SR04 on P1/P2, 18650 battery, USB to the micro:bit's own port.

Per-program detail (architecture, every command, install and verify steps, expected
readback values, tunables) is in `reference.md` next to this file. Read the section for
the program you are working on before changing it.

## Pick the stack first — this decision costs hours if skipped

| Want | Stack | Board program | PC side |
|---|---|---|---|
| Keyboard → faces/servo over **USB** | MicroPython | `main.py` | `keyboard_bridge.py` |
| Keyboard → faces/servo over **Bluetooth** | MakeCode (`pxt`) | `ble/main.ts` | `ble_keyboard_bridge.py` |
| Distance sensor → game/app in the **browser** | MakeCode + Web Serial | `flappy/main.ts` | `flappy/web/` or `kaizen-pushup/` (Chrome/Edge) |
| Distance sensor → **live radar + two servos** | MakeCode + Web Serial | `sentinel/main.ts` | `sentinel/web/` (Chrome/Edge) |
| **All v2 sensors** → dashboard + **5-servo hand** | MakeCode + Web Serial | `handlab/main.ts` | `handlab/web/` (Chrome/Edge) |

**MicroPython has no Bluetooth at all.** `import bluetooth` and `import ubluetooth` both
fail, and `dir(microbit)` has no BLE API — the firmware has no SoftDevice. If the user
asks for wireless, the board must be reflashed with a MakeCode build; MicroPython and the
USB bridge stop existing on the board until it is flashed back. Say this out loud before
flashing, because the flash also wipes the Bluetooth bond.

## Hard constraints (verified on this hardware — do not relearn)

**Board / electrical**
- RobotBit **S1–S8 are PCA9685 I²C channels, not micro:bit pins**: chip at `0x40`,
  S1 = channel 8, S2–S8 = 9–15. No `robotbit` module anywhere. I²C on P19/P20 at 100 kHz.
  Channel register base is `0x06 + 4*ch` (`S1 = 0x26`, `S2 = 0x2A`, … `S5 = 0x36`).
  `sentinel/main.ts` is the two-servo reference; `handlab/main.ts` drives all five through
  the same parameterised `writeChannel`. Keep all servo/display I²C in one fiber so
  channels cannot fight, and stagger multi-servo moves (~15 ms) — five servos off one rail
  at once can reset the RobotBit.
- Servo pulses 600–2400 µs; prescale **121** = 50 Hz. The prescale is lost on power
  cycle, so re-initialise before a move burst (the older programs re-init before every
  move; `sentinel/` does it once per sweep pass and reads PRESCALE back). Registers:
  MODE1 `0x00`, PRESCALE `0xFE`, S1 = channel 8 → `CH8_ON_L = 0x06 + 4*8 = 0x26`.
  OFF values: 0° = `123`, 90° = `307`, 180° = `492`.
- Servo rail needs the **battery and the RobotBit power switch ON**; USB powers only the
  micro:bit. The RobotBit's USB port is charge-only.
- Because of that battery, **unplugging USB does not reboot the micro:bit**. A true power
  cycle is power switch OFF *and* USB out, then USB back in.
- The USB CDC port **renumbers on a power cycle** as well as a re-plug. Re-detect by VID
  `0D28` / PID `0204`; never hardcode a port name (`COMx` on Windows, `/dev/tty*` on
  macOS/Linux).
- The `MICROBIT` drive is DAPLink storage, not a filesystem. Dropping a `.hex` on it
  flashes the board (drive disappears ~1.5 s and returns, no `FAIL.TXT`); copying
  `main.py` there does nothing at all.

**MicroPython path**
- Firmware v2.1.1 (MicroPython 1.18 core); no `compile` builtin; `machine` is minimal.
- `main.py` must be ASCII, contain no `'''` (the installer wraps it in `r'''...'''`),
  and keep every line under 256 chars.
- `scripts/install_servo.py` is the upload path: Ctrl-C → Ctrl-E → write file by lines →
  Ctrl-D → check `FILES`/`LEN` → Ctrl-D. A soft reset re-enumerates USB: wait ~3 s.
- The bridge holds the serial port exclusively — stop it before install/verify, or you
  get an "access denied" / "device busy" error.
- Echo strings `smile` / `frown` / `circle` / `cross` are the bridge's protocol; change
  both sides together.

**MakeCode / Bluetooth path**
- `bluetooth` and `radio` are mutually exclusive (`microbit-dal.bluetooth.enabled`).
  In `ble/pxt.json` keep `core` + `bluetooth` and **remove `radio`**, or the build skips
  bluetooth and every `bluetooth.*` call fails to compile.
- Build with the `makecode` CLI (`npm install -g makecode`). `ble/mkc.json` must pin
  **`https://makecode.microbit.org/`** — *with the trailing slash*. Without it mkc builds
  a broken `ENOTFOUND` URL; the **beta** editor's Bluetooth never delivered UART data.
  Output: `ble/built/binary.hex`.
- NUS characteristic roles are **swapped** from the Nordic convention on the micro:bit:
  write to `6E400003-B5A3-F393-E0A9-E50E24DCCA9E`, echoes arrive on `...0002`.
- **Never drive the servo from the boot path.** Calling `pins.i2cWriteBuffer` during
  startup wedged the program: `BOOT` printed on serial, then BLE never came up. Only move
  the servo on a key press or button.
- Run servo moves inside `control.inBackground(...)` so a stuck I²C bus can't block BLE.
- `serial.writeLine()` over the micro:bit's USB port is free debugging: `BOOT`,
  `CONNECTED`, `DISCONNECTED`, `GOT:`, `SERVO:` lines prove how far the program got when
  BLE says nothing.

## Path A — MicroPython over USB serial

Edit `main.py` (single source of truth), install, verify, run the bridge:

```bash
python scripts/install_servo.py
```

```bash
python scripts/verify_servo.py
```

```bash
python keyboard_bridge.py
```

Servo driver (`main.py` core; for another port change `4*8` to `4*<channel>`):

```python
def servo(angle):                # 0..180 deg -> 600..2400 us
    angle = max(0, min(180, angle))
    _init()                      # MODE1 sleep, PRESCALE 121, wake, 0xA1
    pulse = 600 + angle * 10
    off = (pulse * 4096 + 10000) // 20000
    return _wr(bytes([CH8_ON_L, 0, 0, off & 0xFF, off >> 8]))
```

Verify by reading the chip back, not by looking at the LED matrix:

| Check | Expected |
|---|---|
| `i2c.scan()` | contains `64` |
| PRESCALE `0xFE` | `121` |
| CH8 OFF after k / j / r / x | `307` / `123` / `123` / `492` |
| echo | `smile` / `frown` / `circle` / `cross` |

## Path B — MakeCode over Bluetooth LE

`ble/main.ts` listens on the Nordic UART service, line-delimited: `!k`/`!j`/`!r`/`!x`
are servo commands (echo `smile`/`frown`/`circle`/`cross`), anything else scrolls and
echoes `ACK:<char>`. The `!` prefix is added **by the PC bridge only when Ctrl is held**,
so plain k/j/r/x stay ordinary letters. Buttons A and B run the `!k` and `!x` commands as
a local self-test with no PC involved.

Servo in MakeCode — same PCA9685 sequence, different API (`pins.i2cWriteBuffer` exists as
a shim even though there is no i2c-write-buffer block):

```ts
function pcaWrite(bytes: number[]) {
    let buf = Buffer.create(bytes.length)
    for (let i = 0; i < bytes.length; i++) buf[i] = bytes[i]
    try { pins.i2cWriteBuffer(0x40, buf, false) } catch (e) { }   // RobotBit may be off
}
function moveServo(angle: number) {           // background: never block BLE
    serial.writeLine("SERVO:" + angle)
    control.inBackground(function () { /* PCA init + pulse write */ })
}
```

Build and flash:

```bash
cd ble && makecode
```

```bash
python scripts/flash.py ble/built/binary.hex
```

### The Bluetooth dance that actually works

1. **Start the bridge first** (`run_ble_bridge.sh`/`run_ble_bridge.cmd`, or
   `python ble_keyboard_bridge.py`).
   It scans continuously.
2. If the board has no bond (any reflash wipes it): hold **A+B**, tap reset, keep holding
   2–3 s until `PAIRING MODE!` scrolls, then run
   `python scripts/ble_pair_then_grab.py`.
3. **Tap reset once** with the bridge already running. The program advertises only for a
   short window; a bridge that is already scanning catches it, a bridge started later
   usually misses it and needs another reset.
4. Type. Letters echo `ACK:<char>`; Ctrl+K/J/R/X echo `smile`/`frown`/`circle`/`cross`
   and swing S1.

Rules behind that sequence:

- The board advertises **reliably only in pairing mode**; program-mode advertising is
  brief. Pairing must happen *in* pairing mode — `pair()` against a program-mode board
  fails with bleak `Could not pair with device: 19`.
- Do **not** connect to "peek at services" while the board is in pairing mode; that
  connection drops it out of pairing mode.
- A **stale OS bond** makes the connection drop ~1 s after connecting, before any GATT
  call. Unpair first (Windows/macOS: Settings → Bluetooth; Linux: `bluetoothctl remove
  <MAC>`), then pair again in pairing mode.
- Do not read `client.services` and then reuse the same client — on WinRT this raises
  "The object has been closed". Connect → `start_notify` → write.
- Leftover "everything is paired but nothing connects" usually means the two sides disagree
  about the key: unpair on the OS, pairing mode on the board, pair again.

## Path C — HC-SR04 → USB serial → browser (Web Serial)

For a browser app that reacts to a distance (flappy-bird hand control, pushup counter), the
board reads an **HC-SR04 ultrasonic sensor** and streams the distance; a web page reads it
over the **Web Serial API** and does the app logic. One board firmware drives both apps —
no separate reflash.

**Wiring** (HC-SR04 → micro:bit edge pins, **not** S1–S8):

| HC-SR04 | Connect to |
|---|---|
| VCC | **5 V rail** (next to the servo ports) — not 3.3 V |
| GND | GND |
| TRIG | **P1** |
| ECHO | **P2 through a divider**: 1 kΩ ECHO→P2, 2 kΩ P2→GND (5 V → ~3.3 V) |

ECHO is 5 V; micro:bit pins are 3.3 V and not 5 V tolerant, hence the divider. Powering the
module at 3.3 V instead is safe but many HC-SR04 clones read `0` / are flaky there. Avoid
P0 (buzzer), P16 (RGB LEDs), P19/P20 (I²C to the PCA9685).

- `flappy/main.ts` — board program (MakeCode). `pins.pulseIn(ECHO, High, 30000)` reads the
  HC-SR04 (TRIG=P1, ECHO=P2); `basic.forever` writes `D:<cm>` over USB serial ~20×/s;
  `serial.onDataReceived` flaps S1 on a `f` line; button A flaps once as a local self-test.
  Same PCA9685 driver as `ble/main.ts` (0x40, prescale 121, S1 = channel 8) in
  `control.inBackground`. Build `cd flappy && makecode` → `flappy/built/binary.hex`, flash
  by copying to `D:`. `flappy/pxt.json` is `core` only (no `bluetooth`, no `radio`).
- `flappy/web/index.html` + `flappy/web/game.js` — flappy-bird hand-control game. `run_flappy.sh` /
  `run_flappy.cmd` serves `flappy/web/` on `:8000`. Bird height mirrors the hand (raise = fly up);
  S1 flaps only while the bird moves up.
- `kaizen-pushup/` — pushup counter app (reuses the `flappy` firmware). Sensor on the floor
  pointed at the chest: down < 2 in, up > 5 in (and < 1.5 m); a rep = down → up. Counts reps
  down to a target, beeps + speaks each stage/rep, celebrates on completion.
  `run_kaizen_pushup.sh` / `run_kaizen_pushup.cmd` serves it on `:8001`.

Protocol (the contract): board → browser `D:<cm>` lines; browser → board `f\n` (flap).

**Web Serial is Chrome/Edge only and needs a secure context** — serve on `localhost`
(`python -m http.server`), never `file://`. It opens the serial port **exclusively**, so
`serial_watch.py` / the MicroPython bridge fail with an "access denied" error while the
browser is connected, and vice-versa.

**Spurious readings (reuse this):** a bare HC-SR04 returns `0` when nothing is in range and
emits brief far echoes (pointed at the ceiling, or the person leaves the beam) that spike
the distance. Filter in the **browser**, not the board: discard `0` and anything over a max
(flappy `MAX_VALID_CM = 40`; pushup `MAX_RANGE_CM = 150`), then smooth with a
median-of-3 (`DIST_SAMPLES`). The board just streams honest raw `cm`.

## Path D — dual-servo radar + guard arm (Sonar Sentinel)

`sentinel/` is the reference for driving **two** PCA9685 channels plus the sensor. S1 pans
the HC-SR04 20°–160°; S2 is a guard arm (20° open / 160° locked). A browser draws the live
radar; `run_sentinel.sh` / `run_sentinel.cmd` serves it on **:8002**. Verified end to end on this hardware:
echoes, alarm latch/release, both servos, and the Web Serial scope. The port moves after a
power cycle — the probe and the page's Connect picker auto-detect it.

- Firmware rules: one `basic.forever` fiber owns **all** I²C and display work; the serial
  handler and buttons only set globals. `pcaInit()` runs at the start of each sweep pass and
  reads PRESCALE back (`SYS:READY,PCA=OK|ERR`). Sweep step = move → `basic.pause(45)` →
  `pulseIn(30 ms)` → emit → step ±5°, with `N:<cm>` at each turnaround.
- Alarm: any sample under `keepOutCm` latches S2; release only 2.6 s after the last threat
  (over one sweep), so a hand anywhere in the field keeps it closed. The LED matrix shows a
  1–5 column proximity bar, a dot when clear, an X on alarm — redraw only on level change.
- Protocol: board `A:<deg>,D:<cm>` · `N:<cm>` · `ALARM:<0|1>` · `K:<cm>` · `ACK:<cmd>` ·
  `SYS:READY,PCA=…,ALARM=…` · `SYS:SWEEP|PAUSED|PARK|TEST`; browser `t:<cm> s p c w i d`.
- **Sensor diagnostic**: `d` triggers once with a 100 ms window and prints `DIAG:US=<µs>`.
  A live HC-SR04 with no target holds ECHO high ~38 ms (≈38000); `0` means unpowered,
  ungrounded or miswired. Remember `PCA=OK` proves only the 3.3 V I²C side — the 5 V servo
  rail (battery + power switch) is separate.
- Verify: `python scripts/radar_probe.py` (auto-detects the port, 12 s) or
  `python scripts/radar_probe.py <port> 20`; close the browser first — Web Serial is
  exclusive. It checks the handshake, rate, angle range, reversals and reports PASS/FAIL.

## Path E — all v2 sensors → dashboard + 5-servo hand (HandLab)

`handlab/` streams every v2 sensor (temperature, light, mic, 3-axis accelerometer, 3-axis
magnetometer) plus sonar to a browser over Web Serial, and the same page drives five servos
as a hand. `run_handlab.sh` / `run_handlab.cmd` serves it on **:8003**. Built for a **second** board,
independent of the Sentinel board.

- **Servo map**: S1–S5 = PCA9685 channels 8–12 = Thumb/Index/Middle/Ring/Pinky. Servos
  home to **0°** (`HOME = 0`), slider range 0–180°; the `home` command (Button B too)
  returns all five to 0°. **There are deliberately no preset poses** — moving all five at
  once reset the RobotBit (power surge). Firmware = one `basic.forever` fiber owning all
  I²C/display, telemetry every ~100 ms, moves staggered one channel per ~15 ms tick.
- **Protocol**: board `S T=.. L=.. MIC=.. AX/AY/AZ=.. HX/HY/HZ=.. D=..` · `PCA=OK|ERR` ·
  `ACK:<cmd>` · `SERVO n=<deg>`; browser `s1:<deg> .. s5:<deg>` · `home` · `i`.
- **Magnetometer/compass**: never call `input.compassHeading()` / `input.calibrateCompass()`
  — they hang boot (see Troubleshooting). Read raw `input.magneticForce()` and derive the
  heading client-side; the browser's **Compass North Reset** re-baselines it.
- **Browser visuals**: a **3D micro:bit model** (5×4×0.3 cm prism) that tilts with the
  accelerometer in its **standing** pose (Y up: `pitch = atan2(az, ay)`,
  `roll = atan2(ax, ay)`), and a **compass** with a smoothed needle. The other tiles keep
  line-graph sparklines. Demo mode feeds synthetic standing-pose data.
- Verify: `python scripts/handlab_probe.py` (auto-detects port, 12 s). Expect `PCA=OK`,
  ~10 samples/s, steady magnetic-field magnitude (~50–200 µT), `SERVO` echoes, and the
  standing accel `AY≈1024, AX≈-100, AZ≈-20`.

## Verification when the radio is being difficult

- **Buttons A/B** exercise the same command handler as Bluetooth (happy+90°, X+180°).
  That proves the program, display and PCA9685 without any PC.
- **USB serial** (`scripts/serial_watch.py 60`, auto-detects the port) shows `BOOT`, `CONNECTED`, `GOT:`,
  `SERVO:` — enough to tell a dead program from a dead link.
- `scripts/ble_scan_watch.py 60` logs any micro:bit advertisement with timestamps;
  `scripts/ble_pair_then_grab.py` unpairs, pairs on sight, then chases the program.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `import bluetooth` fails | MicroPython has no BLE. Flash a MakeCode build (Path B). |
| MakeCode build: "skipping bluetooth ... conflicts with radio" | Remove `radio` from `pxt.json`. |
| mkc: `ENOTFOUND makecode.microbit.org---asseteditor` | `targetWebsite` needs a trailing slash. |
| BOOT prints then BLE never appears | Servo I²C ran at boot and wedged the program; move it behind a key/button. |
| Connect succeeds, drops after ~1 s | Stale OS bond. Unpair the device, pair again in pairing mode. |
| Board not found at all | It is not advertising: pairing mode, or start the bridge then reset. |
| `Could not pair with device: 19` | Board is in program mode; pairing only works in pairing mode. |
| Subscribed/echo works, then dead | Reboot wiped the advertising window; start bridge first, then reset. |
| Install: "access denied" / "device busy" | Bridge/monitor holds the serial port; stop it. |
| Faces work, servo dead | Battery / power switch; or the RobotBit is off and I²C writes are swallowed. |
| Servo buzzes at 0° | 600 µs is at the mechanical limit; raise the minimum to ~700 µs. |
| `i2c.scan()` misses 64 | RobotBit off, unseated, or I²C pins not contacting. |
| Radar `D:` always 0, `DIAG:US=0` | Sensor unpowered/miswired: 5 V rail (battery + switch), GND, P1=TRIG / P2=ECHO, ECHO divider. A live HC-SR04 with no target reads ≈38000 µs. |
| Radar `PCA=ERR` | PCA9685 did not answer the prescale read-back: RobotBit off/unseated. The sensor stream can still run. |
| MakeCode board boots but emits nothing | `input.compassHeading()` / `calibrateCompass()` hang boot on this hardware — use `input.magneticForce()` (raw µT) and derive heading client-side. A module-scope `serial.writeLine` can also be dropped before USB CDC is ready; emit from the loop or after a ~500 ms pause. |
| Moving all 5 servos at once resets the RobotBit | Power surge on the shared 5 V rail. Stagger the moves (~15 ms apart) and avoid multi-servo preset poses — HandLab has none for this reason. |

## Files

- `main.py` — MicroPython board program (source of truth for Path A).
- `keyboard_bridge.py` / `run_bridge.sh`, `run_bridge.cmd` — USB serial bridge (K/J/R/X).
- `ble/main.ts`, `ble/pxt.json`, `ble/mkc.json`, `ble/built/binary.hex` — MakeCode build (Path B).
- `ble_keyboard_bridge.py` / `run_ble_bridge.sh`, `run_ble_bridge.cmd` — BLE bridge (A–Z, 0–9, Ctrl commands).
- `flappy/main.ts`, `flappy/pxt.json`, `flappy/built/binary.hex` — HC-SR04 distance stream + S1 flap (Path C board program).
- `sentinel/main.ts`, `sentinel/built/binary.hex` — two-servo radar + guard arm (Path D board program).
- `sentinel/web/`, `run_sentinel.sh`, `run_sentinel.cmd` — radar scope on `:8002`; `scripts/radar_probe.py` — serial protocol probe.
- `handlab/main.ts`, `handlab/built/binary.hex` — 5-servo hand + sensor stream (Path E board program).
- `handlab/web/`, `run_handlab.sh`, `run_handlab.cmd` — dashboard on `:8003`; `scripts/handlab_probe.py` — telemetry/servo probe.
- `flappy/web/index.html`, `flappy/web/game.js`, `run_flappy.sh`, `run_flappy.cmd` — flappy hand-control game (Web Serial, `:8000`).
- `kaizen-pushup/` — Kaizen pushup counter app (reuses `flappy` firmware) + `run_kaizen_pushup.sh`, `run_kaizen_pushup.cmd` (`:8001`).
- `scripts/install_servo.py`, `verify_servo.py` — upload + readback; `scripts/flash.py` — flash a `.hex`; `scripts/microbit_util.py` — port/volume auto-detect.
- `scripts/serial_watch.py`, `ble_scan_watch.py`, `ble_pair_then_grab.py` — diagnostics.
- `scripts/archive/` — bring-up leftovers (old probes, old installers); reference only, many hardcode COM6/COM7.
- `requirements.txt` — Python dependencies (`pyserial`, `bleak`, `pynput`).
- `firmware/micropython-microbit-v2.1.1.hex` — restore MicroPython (then re-run the installer).
- `CLAUDE.md` — short project page (state check, program list, rules); `reference.md` in
  this folder — full detail for every program; `BLE.md` — user-facing how-to-run.
