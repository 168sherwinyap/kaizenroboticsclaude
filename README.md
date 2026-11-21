# Kaizen Robotics: micro:bit and RobotBit with Claude Code

[![MakeCode build](../../actions/workflows/makecode.yml/badge.svg)](../../actions/workflows/makecode.yml)
![Board: micro:bit v2](https://img.shields.io/badge/board-micro%3Abit%20v2-00a4a6)
![Firmware: MakeCode and MicroPython](https://img.shields.io/badge/firmware-MakeCode%20%7C%20MicroPython-6f42c1)
![Web Serial: Chrome and Edge](https://img.shields.io/badge/Web%20Serial-Chrome%20%7C%20Edge-1a73e8)

This repository holds working programs for a BBC micro:bit v2 on a KittenBot RobotBit
board, with servo motors and an HC-SR04 distance sensor. It also holds the instructions
about this hardware that Claude Code reads at the start of a session.

## Requirements

- A micro:bit v2 on a RobotBit, with the 18650 battery fitted
- A USB data cable
- Claude Code
- Chrome or Edge, because the browser apps use Web Serial and other browsers do not support it
- Python 3 (with `pip install -r requirements.txt`), which serves the browser apps and
  runs the scripts that check the board
- Optional: Node.js and `npm install -g makecode`, needed only to build a changed board
  program

PC-side tooling is cross-platform: Python scripts (run `pip install -r requirements.txt`)
with a `.sh` launcher for macOS/Linux and a `.cmd` launcher for Windows. The serial port is
auto-detected; the micro:bit mounts as a drive labelled `MICROBIT`.

On macOS and Linux, run `./setup.sh` once after cloning instead of `pip install`. It
creates a `.venv` folder with the Python packages in it. Run the scripts with
`.venv/bin/python` where this page says `python`. The `.sh` launchers already do this.

## First run

1. Clone this repository.
2. Open a terminal in the repository folder.
3. Start a new Claude Code session in that folder with `claude`. Claude Code loads
   `CLAUDE.md` and the `kaizenrobotics` skill only when a session starts in this folder.
4. Plug the USB cable into the micro:bit's own USB port. USB on the RobotBit only charges
   the battery.
5. Switch the RobotBit power on. Servos get their power from the battery, and USB powers
   only the micro:bit.
6. Tell Claude Code what you want to build.

## Programs

| Program | What it does | Folder |
|---|---|---|
| Faces and servo | Keyboard keys show a face on the micro:bit and move a servo, over USB | `main.py`, `keyboard_bridge.py` |
| Bluetooth keyboard mirror | Typed keys scroll on the micro:bit, over Bluetooth | `ble/` |
| Flappy Bird hand control | Your hand height above the sensor moves the bird in a browser game | `flappy/` |
| Pushup counter | Counts pushups with the distance sensor, in the browser | `kaizen-pushup/` |
| Sonar Sentinel | A servo sweeps the sensor and a browser page draws a radar; a second servo closes a guard arm | `sentinel/` |
| HandLab | A browser dashboard shows every micro:bit sensor and moves five servos as a hand | `handlab/` |

Each MakeCode folder has a built program file at `built/binary.hex`. Run
`python scripts/flash.py <folder>/built/binary.hex` (or copy that file to the MICROBIT
drive) to load it onto the board.

## Documentation

- `CLAUDE.md` lists the programs, the check for what is on a board, and the rules that
  apply to every program.
- `.claude/skills/kaizenrobotics/SKILL.md` has the hardware constraints and a
  troubleshooting table.
- `.claude/skills/kaizenrobotics/reference.md` has the commands, wiring and serial
  protocol for each program.
- `BLE.md`, `sentinel/README.md`, `handlab/README.md` and `kaizen-pushup/README.md` are
  how-to pages for those programs.
