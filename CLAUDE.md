# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Not a software project: a hardware control setup for a BBC micro:bit v2.2 mounted on a
KittenBot RobotBit 2.2, with 180° hobby servos on ports S1-S5 (S1-S8 available) and an
HC-SR04 ultrasonic sensor on P1 (TRIG) / P2 (ECHO). There is no build system or test
framework. Each program has a board side and a PC side that talk over a line-based serial
protocol.

**Load the `kaizenrobotics` skill before any work here.** It holds the stack choice, the
hard constraints and the troubleshooting table. Per-program detail (architecture, commands,
install and verify steps, protocols) is in `.claude/skills/kaizenrobotics/reference.md`.

## Current state: unknown

Do not assume which program is on the board that is plugged in. Find out before building
on it: read the USB serial port at 115200 for a few seconds
(`python scripts/serial_watch.py 5`; on macOS and Linux
`.venv/bin/python scripts/serial_watch.py 5`) and match the output.

| Serial output | Program on the board |
|---|---|
| `S T=.. L=.. MIC=..` lines, ~10/s | HandLab (`handlab/`) |
| `A:<deg>,D:<cm>` lines | Sonar Sentinel (`sentinel/`) |
| `D:<cm>` lines only, ~20/s | Flappy (`flappy/`), also used by `kaizen-pushup/` |
| Nothing until reset, then `BOOT` | Bluetooth keyboard mirror (`ble/`) |
| Nothing; Ctrl-C gives a `>>>` prompt | MicroPython (`main.py`, or an empty filesystem) |

If the output matches none of these, flash the program you need.

## Programs

| Program | Board side | PC side | Link |
|---|---|---|---|
| Faces + S1 servo from the keyboard | `main.py` (MicroPython) | `keyboard_bridge.py`, `run_bridge.sh` / `run_bridge.cmd` | USB serial |
| Bluetooth keyboard mirror | `ble/main.ts` (MakeCode) | `ble_keyboard_bridge.py`, `run_ble_bridge.sh` / `run_ble_bridge.cmd` | BLE UART |
| Flappy Bird hand control | `flappy/main.ts` | `flappy/web/`, `run_flappy.sh` / `run_flappy.cmd` (`:8000`) | Web Serial |
| Kaizen pushup counter | reuses `flappy/built/binary.hex` | `kaizen-pushup/` (`:8001`) | Web Serial |
| Sonar Sentinel: radar + guard arm | `sentinel/main.ts` | `sentinel/web/`, `run_sentinel.sh` / `run_sentinel.cmd` (`:8002`) | Web Serial |
| HandLab: all v2 sensors + 5-servo hand | `handlab/main.ts` | `handlab/web/`, `run_handlab.sh` / `run_handlab.cmd` (`:8003`) | Web Serial |

All of them were verified end to end on the author's hardware. Each MakeCode folder keeps
its flashable build at `built/binary.hex`; `python scripts/flash.py <folder>/built/binary.hex`
copies it onto the MICROBIT volume. Rebuild with `cd <folder> && makecode`
(`npm install -g makecode`).

PC-side tooling is cross-platform: Python scripts (`pip install -r requirements.txt`) plus a
`.sh` launcher for macOS/Linux and a `.cmd` launcher for Windows. The serial port is
auto-detected by USB VID `0D28` / PID `0204` (`COMx` on Windows, `/dev/tty.usbmodem*` on
macOS, `/dev/ttyACM*` on Linux); the micro:bit's filesystem mounts as a drive labelled
`MICROBIT` (`/Volumes/MICROBIT` on macOS, `/media/<user>/MICROBIT` on Linux).

**On macOS and Linux, run `./setup.sh` once before anything else.** It creates `.venv` and
installs `requirements.txt` into it. Then run every script with `.venv/bin/python`, wherever
these documents say `python`: a stock Mac has no `python` or `pip` command, and Homebrew's
Python refuses a plain `pip install`. The `.sh` launchers use `.venv` by themselves and open
the page in Chrome or Edge, because Safari and Firefox have no Web Serial.

## Rules that apply to every program

- RobotBit **S1-S8 are PCA9685 I2C channels at 0x40, not micro:bit pins** (S1 = channel 8).
  No `robotbit` module exists; each program carries an inline driver.
- Servos need the RobotBit's 18650 battery and its power switch ON. USB powers only the
  micro:bit. Program through the micro:bit's own USB port; the RobotBit's port only charges.
- HC-SR04: VCC on the 5 V rail, TRIG = P1, ECHO = P2 through a 1 kΩ / 2 kΩ divider.
  micro:bit pins are not 5 V tolerant.
- Never hardcode a serial port. Detect the micro:bit by USB VID `0D28` / PID `0204`; the
  port renumbers on a re-plug or a power cycle.
- A serial port has one owner at a time: the browser page (Web Serial), a bridge, or a
  probe. Close the others first.
- Web Serial is Chrome/Edge only and needs `localhost`, never `file://`.
- MicroPython on the micro:bit has no Bluetooth. Wireless means a MakeCode build.
- Do not call `input.compassHeading()` or `input.calibrateCompass()`: they hang this board
  at boot. Read `input.magneticForce()` instead.
- Do not move five servos in the same instant: the current surge resets the RobotBit.
  Stagger the moves (~15 ms apart).

## Files

- `.claude/skills/kaizenrobotics/SKILL.md`: stack choice, hard constraints, troubleshooting.
- `.claude/skills/kaizenrobotics/reference.md`: full detail for every program.
- `scripts/`: `install_servo.py` + `verify_servo.py` (MicroPython upload and readback),
  `flash.py` (copy a `.hex` onto the MICROBIT volume), `microbit_util.py` (port/volume
  auto-detect), `radar_probe.py` + `handlab_probe.py` (serial protocol checks with
  PASS/FAIL), `serial_watch.py`, `ble_scan_watch.py`, `ble_pair_then_grab.py`.
- `keyboard_bridge.py` (USB keyboard → face/servo bridge) and `requirements.txt` (Python deps).
- `scripts/archive/`: bring-up leftovers, reference only. Many hardcode COM6/COM7 and the
  installers in there embed older copies of the board program.
- `firmware/micropython-microbit-v2.1.1.hex`: restores MicroPython.
- `BLE.md`, `sentinel/README.md`, `handlab/README.md`, `kaizen-pushup/README.md`:
  operator how-tos.
- `.claude/launch.json`: dev-server entries for the Claude app's browser pane (flappy
  `:8000`, kaizen-pushup `:8001`, sentinel `:8002`, handlab `:8003`).
