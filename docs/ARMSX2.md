# Lloyd ↔ ARMSX2 (PS2) Agent API

Lloyd does **not** ship the full ARMSX2 binary. He talks to a PS2 session through a **normal HTTP API** (same style as TextFiction / vision / audio).

## Upstream (open source)

| Project | Link |
|---------|------|
| **ARMSX2** | https://github.com/ARMSX2/ARMSX2 |
| Org | https://github.com/ARMSX2 |
| Docs | https://docs.armsx2.net/ |
| License | **GPL-3.0** (PCSX2-based) |

You run ARMSX2 (or desktop PCSX2) yourself. Lloyd connects **under the hood** via `/emu/*` on `server.py`.

## Legal

- Provide your **own** PS2 BIOS dump from a console you own.
- Provide **legally obtained** game dumps (your discs).
- Lloyd never distributes BIOS or ISOs.

## Architecture

```
┌─────────────┐   HTTP    ┌──────────────────┐   queue / plugin   ┌────────────┐
│ Lloyd agent │ ◄──────► │ /emu/* bridge     │ ◄───────────────► │ ARMSX2 /   │
│ (NumPy mind)│          │ vision audio act  │                   │ PCSX2 host │
└─────────────┘          └──────────────────┘                   └────────────┘
```

### Agent loop

1. **Vision** – host posts a frame (screenshot / capture) → Lloyd remembers / can train patterns  
2. **Audio** – optional transcript or level → memory  
3. **Decide** – Lloyd reads state and picks DualShock buttons / sticks  
4. **Action** – inputs sit in a queue; host injector applies them to the emulator  
5. **Learn** – trajectory dumped to trainer + memory  

## API (on Lloyd `server.py`)

Base URL: same as chat, e.g. `http://PHONE_IP:8080`

| Method | Path | Body / query | Purpose |
|--------|------|--------------|---------|
| GET | `/emu/status` | — | Bridge health + sessions |
| GET | `/emu/state?session=default` | — | Last frame meta, audio, actions |
| GET | `/emu/inputs?session=default` | — | **Host drains** controller queue |
| POST | `/emu/frame` | JSON | Push vision |
| POST | `/emu/audio` | JSON | Push audio |
| POST | `/emu/action` | JSON | Queue controller input |
| POST | `/emu/decide` | JSON | Lloyd chooses action from state |
| POST | `/emu/play` | JSON | One full agent step |
| POST | `/emu/learn` | JSON | Train on session trajectory |

### Vision example

```bash
curl -X POST http://127.0.0.1:8080/emu/frame \
  -H 'Content-Type: application/json' \
  -d '{
    "session": "gt4",
    "game": "Gran Turismo 4",
    "caption": "menu: arcade mode highlighted",
    "width": 640,
    "height": 448,
    "image_b64": ""
  }'
```

`image_b64` optional for now (caption is enough for text mind). Binary frames supported for future vision nets.

### Action example

```bash
curl -X POST http://127.0.0.1:8080/emu/action \
  -H 'Content-Type: application/json' \
  -d '{
    "session": "gt4",
    "buttons": ["cross"],
    "sticks": {"left_x": 0.2, "left_y": -0.5},
    "hold_ms": 100
  }'
```

**Buttons:** `cross circle square triangle l1 l2 l3 r1 r2 r3 start select home dpad_up dpad_down dpad_left dpad_right`

**Sticks:** `left_x left_y right_x right_y` in `[-1, 1]`

### Lloyd decides + plays

```bash
curl -X POST http://127.0.0.1:8080/emu/decide \
  -H 'Content-Type: application/json' \
  -d '{"session":"gt4","goal":"enter arcade mode"}'

curl -X POST http://127.0.0.1:8080/emu/play \
  -H 'Content-Type: application/json' \
  -d '{"session":"gt4","goal":"win the race"}'
```

### Learn

```bash
curl -X POST http://127.0.0.1:8080/emu/learn \
  -H 'Content-Type: application/json' \
  -d '{"session":"gt4","steps":24}'
```

### Host injector (pull model)

Any external process (Python script, future ARMSX2 plugin, ADB tap layer) polls:

```bash
curl 'http://127.0.0.1:8080/emu/inputs?session=gt4'
```

and applies `buttons` / `sticks` to the running emulator.

## Chat commands (via `/chat`)

| Say | Effect |
|-----|--------|
| `ps2 status` / `emu status` | Bridge status |
| `ps2 learn` | Train on default session |
| `ps2 play` / `play ps2` | One decide+act step |

## Why not embed full ARMSX2 in this repo?

- ARMSX2 is a large **C++ / PCSX2** tree (GPL-3.0).
- Building it needs NDK / CMake / device-specific toolchains.
- Lloyd stays portable (Termux, VPS, Colab) with a **thin bridge**.
- Integration path: host capture + input queue today → optional native plugin later.

## Vision / audio training

Same paths as the rest of Lloyd:

- Frame captions → `lloyd.remember` + `/emu/learn` text trajectory  
- Optional raw `image_b64` stored for future pattern / vision training (see `/vision`)  
- Audio transcripts feed the same memory/trainer pipeline as `/audio`  

## Quick start

```bash
# Terminal 1 — Lloyd
python server.py

# Terminal 2 — simulate a frame + agent step
curl -X POST http://127.0.0.1:8080/emu/frame -H 'Content-Type: application/json' \
  -d '{"session":"demo","game":"Demo","caption":"title screen, press start"}'
curl -X POST http://127.0.0.1:8080/emu/play -H 'Content-Type: application/json' \
  -d '{"session":"demo","goal":"start the game"}'
curl 'http://127.0.0.1:8080/emu/inputs?session=demo'
curl -X POST http://127.0.0.1:8080/emu/learn -H 'Content-Type: application/json' \
  -d '{"session":"demo"}'
```

Install ARMSX2 from upstream releases when you want real hardware rendering; point a capture script at `/emu/frame` and an input script at `/emu/inputs`.
