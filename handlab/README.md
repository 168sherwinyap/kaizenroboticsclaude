# HandLab

A sensor dashboard and five-finger robot hand for a **second** micro:bit v2 + KittenBot
RobotBit (separate from the Sentinel board). The board streams every v2 sensor to a
browser over Web Serial; the same page drives five servos as a hand.

- **Sensors:** temperature, light, microphone, 3-axis accelerometer, 3-axis magnetometer
  (+ compass heading), and the HC-SR04 sonar distance.
- **Servos:** S1–S5 = Thumb, Index, Middle, Ring, Pinky, driven by per-finger sliders.

## Wiring

| Servo | PCA channel | Finger |
|---|---|---|
| S1 | 8 | Thumb |
| S2 | 9 | Index |
| S3 | 10 | Middle |
| S4 | 11 | Ring |
| S5 | 12 | Pinky |

HC-SR04: VCC on the **5 V rail**, GND, TRIG→**P1**, ECHO→**P2** through a 1 kΩ series +
2 kΩ to GND divider. RobotBit 18650 in and power switch **ON** (servo rail). Servos run
0°–180°, home = 0°.

## Build, flash, run

```bash
cd handlab
makecode
```

```bash
# from the repository root
python scripts/flash.py handlab/built/binary.hex
```

Then run `./run_handlab.sh` (macOS/Linux) or `run_handlab.cmd` (Windows) and click
**Connect board**. Chrome/Edge only.

## Controls

- **Sliders** drive each finger directly (0–180°).
- **Home** returns all five servos to 0°.
- **Compass North Reset** re-baselines North to the current orientation (client-side).
- **Board buttons:** A cycles the LED-matrix readout (sound → light → magnetic field →
  tilt bubble), B homes the servos (0°).

## Protocol

```
board ->  S T=<c> L=<0-255> MIC=<0-255> AX/AY/AZ=<mg> HX/HY/HZ=<uT> D=<cm>
          PCA=OK|ERR   ACK:<cmd>   SERVO <n>=<deg>
browser -> s1:<deg> .. s5:<deg>   home   i
```

**Magnetometer note:** the firmware reads the raw magnetometer with
`input.magneticForce()`; it deliberately does **not** call `input.compassHeading()` or
`input.calibrateCompass()`, which hang the boot on this board (verified). The dashboard
derives a heading from `HX`/`HY` and the **Compass North Reset** button re-baselines it.

## Verify without a browser

Close the browser tab first (Web Serial owns the port exclusively):

```
python scripts/handlab_probe.py 15
python scripts/handlab_probe.py 20 --send "2:s1:150;5:s5:30;8:home"
```

Expected: `PCA=OK`, ~10 sensor samples/s, a steady magnetic-field magnitude (~50–200 µT),
and `SERVO` echoes after each command.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `PCA=ERR`, no servo motion | 18650 empty/absent, power switch off, or board not seated |
| Servo buzzes at an end | Angle at a stop — keep it 0°–180°, re-home |
| Heading wanders | Servo current disturbs the field; re-baseline with **Compass North Reset** |
| No Web Serial | Chrome/Edge on `http://127.0.0.1:8003`, not `file://` |
| Port busy | The browser or `handlab_probe.py` holds it; close that first |
| Sonar always 0 | Hand/box 10–40 cm in front; 5 V rail powered; TRIG/ECHO not swapped |
