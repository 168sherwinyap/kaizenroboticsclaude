# Sonar Sentinel

A live sonar radar for the micro:bit v2 on a KittenBot RobotBit 2.2, with two servos.

- **S1** pans an HC-SR04 through a 20°–160° sweep.
- **S2** is a guard arm that locks when something stays inside a keep-out distance.
- The micro:bit streams angle + distance over USB serial; a browser draws a phosphor
  radar scope with fading blips, a real sweep line, a draggable keep-out ring and a
  guard-arm animation you can hear.

```
        radar scope                         guard arm (S2)
     .  *  .        live blips          ┌───────────────┐
   *   ( )   .      range rings          │  OPEN / LOCKED │
  .   SWEEP   *     keep-out ring        └───────────────┘
     .  .  .        sonar ping
        ▲
     S1 pans the sensor
```

## Wiring

| HC-SR04 | Connect to |
|---|---|
| VCC | **5 V rail** next to the servo ports |
| GND | GND |
| TRIG | **P1** |
| ECHO | **P2 through a divider**: 1 kΩ ECHO→P2, 2 kΩ P2→GND |

Servos in **S1** (pan) and **S2** (guard arm). The RobotBit needs its 18650 battery and
the power switch **ON** — USB alone powers only the micro:bit, so the servos and the
5 V sensor rail stay dead. Mount the HC-SR04 on the S1 horn facing outward.

## Build, flash, run

```bash
cd sentinel
makecode
```

```bash
# from the repository root
python scripts/flash.py sentinel/built/binary.hex
```

(the MICROBIT volume is DAPLink storage: the file vanishes and the board reboots when the
flash succeeds; retry on `FAIL.TXT`)

Then run `./run_sentinel.sh` (macOS/Linux) or `run_sentinel.cmd` (Windows) at the repo
root, click **Connect board**, and pick the micro:bit port. Chrome or Edge only — Web
Serial needs `localhost`.

## Controls

| Action | Page | Board |
|---|---|---|
| Start / pause sweep | Space, **Pause** button | **A** |
| Wiggle both servos | W, **Wiggle** button | **B** |
| Center (90°, arm open) | C, **Center** button | — |
| Set keep-out distance | slider or drag the amber ring | `t:<cm>` over serial |
| Sensor self-check | **Sensor check** button | `d` over serial |
| Mute ping | M | — |

The LED matrix shows a proximity bar (1–5 columns), a dot when the field is clear, and an
X on alarm.

## Protocol

Board → browser, newline delimited:

```
A:<deg>,D:<cm>              one per sweep step, D:0 = no echo
N:<cm>                      nearest valid distance of that pass
ALARM:<0|1>                 on alarm edges only
K:<cm>                      keep-out echo
ACK:<command>               echo of every command
DIAG:US=<raw echo us>       reply to the d sensor check
SYS:READY,PCA=OK|ERR,ALARM=0|1
SYS:SWEEP|PAUSED|PARK|TEST
```

Browser → board:

```
t:<cm>   s   p   c   w   i   d
```

`d` measures one raw echo with a 100 ms window: a live HC-SR04 with nothing in front
holds ECHO high ~38 ms (`DIAG:US≈38000`); `DIAG:US=0` means it is unpowered, ungrounded
or miswired.

`PCA=ERR` means the PCA9685 did not answer — usually the RobotBit is off or unseated. The
sensor stream keeps working; the servos will not.

## Verify without a browser

Close the browser tab first (Web Serial owns the port exclusively):

```
python scripts/radar_probe.py 15
python scripts/radar_probe.py 25 --send "2:i;5:t:40;10:p;14:s;18:w"
```

(the probe auto-detects the serial port)

## Troubleshooting

| Symptom | Fix |
|---|---|
| Every `D:` is 0 | Hand/box 10–40 cm in front; check the 5 V rail (battery switch ON); confirm P1=TRIG, P2=ECHO; check the ECHO divider |
| `PCA=ERR`, no servo motion | Battery missing/empty, RobotBit switch off, or the board is not seated |
| Servo buzzes at an end | Angle is at the mechanical limit; change `ARM_OPEN`/`ARM_LOCKED` in `main.ts` |
| Sweep feels slow | `SETTLE_MS` in `main.ts`; `pulseIn` also blocks up to 30 ms with no echo |
| Page says NO WEB SERIAL | Use Chrome/Edge on `http://127.0.0.1:8002` (not `file://`) |
| Port busy | The browser or `radar_probe.py` holds it; close that first |

## Going back

The Flappy Bird firmware is still at `flappy/built/binary.hex`. Running
`python scripts/flash.py flappy/built/binary.hex` restores that demo; MicroPython is
restored with `firmware/micropython-microbit-v2.1.1.hex` plus
`python scripts/install_servo.py`.
