# Kaizen Pushup Counter

A browser app that counts pushups using the micro:bit + HC-SR04 ultrasonic sensor.

## How it works

- The micro:bit runs the `flappy` hand-control firmware (`../flappy/built/binary.hex`),
  which streams `D:<cm>` over USB serial ~20×/s.
- The HC-SR04 sits **on the floor, pointed up at your chest**.
  - **Down stage** = distance < 2 in (chest near the floor).
  - **Up stage** = distance > 5 in (chest raised) but < 1.5 m.
  - One rep = down → up.
- The browser reads the stream over **Web Serial**, counts reps down to your target, beeps
  on each stage transition, and celebrates (confetti + fanfare) when you hit the target.

## Wiring (same as the flappy app)

| HC-SR04 | Connect to |
|---|---|
| VCC | 5 V rail (next to the servo ports) — not 3.3 V |
| GND | GND |
| TRIG | P1 |
| ECHO | P2 through a divider: 1 kΩ ECHO→P2, 2 kΩ P2→GND (5 V → ~3.3 V) |

## Run

1. Make sure the board is flashed with `../flappy/built/binary.hex`.
2. Run `./run_kaizen_pushup.sh` (macOS/Linux) or `run_kaizen_pushup.cmd` (Windows) —
   serves this folder on `:8001`.
3. Open in Chrome/Edge, **Connect** the board, set target + sets, **Start**.

## Tunables

At the top of `app.js`: `DOWN_IN` (2), `UP_IN` (5), `MAX_RANGE_CM` (150 = 1.5 m),
`DIST_SAMPLES` (3). Readings above `MAX_RANGE_CM` (or `0`) are ignored so a sensor briefly
pointed at the ceiling — or the person leaving the sensor's range — can't spike the count.
