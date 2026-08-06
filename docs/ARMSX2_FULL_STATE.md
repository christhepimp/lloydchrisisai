# Full-state PS2 → Lloyd mind (any game)

Every tick the host sends **everything the game produces**. Lloyd stores it in memory and trains on it — same agent path as chat / Moltbook / crypto APIs.

## What gets fed each tick

| Channel | Content |
|---------|---------|
| Vision | pixels (`image_b64`) and/or caption |
| Audio | transcript / level / pcm |
| Live values | score, health, x/y/z, screen_id, flags, timer, … |
| Memory | generic RAM reads (any address) |
| Action | buttons + sticks Lloyd (or host) just used |
| Reaction | outcome / reward / event from the game |
| Timing | wall clock + optional in-game time |

**Generic:** no hard-coded title. Per-game `emu_rules/*.json` maps labels → RAM addresses.

## Main endpoint

```http
POST /emu/tick
Content-Type: application/json

{
  "session": "gt4",
  "game": "Gran Turismo 4",
  "t_game": 123.45,
  "frame": { "caption": "race: turn 3, car ahead", "width": 640, "height": 448 },
  "audio": { "transcript": "engine high rpm", "level": 0.7 },
  "values": { "score": 12000, "health": 88, "x": 10.2, "y": 0.1, "screen_id": 3 },
  "mem": {
    "reads": [
      { "label": "score", "addr": "0x20F000", "type": "u32", "data_b64": "..." }
    ]
  },
  "reaction": { "lap_complete": false, "crash": false, "reward": 0.1 },
  "note": "optional"
}
```

**Response** includes `mind_line` and `fed_to_mind: true`. Every tick is `lloyd.remember(...)`; every N ticks also does a short trainer pass.

## Other endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/emu/values` | live values only |
| POST | `/emu/memread` | generic RAM reads |
| POST | `/emu/rules` | load label→addr map for this game |
| POST | `/emu/frame` `/emu/audio` `/emu/action` | single channels |
| GET | `/emu/state` | full session dump |
| POST | `/emu/play` `/emu/decide` | agent acts using **values + vision** |
| POST | `/emu/learn` | batch train on full trajectory |
| GET | `/emu/inputs` | host drains controller queue |

## Rules file (any game)

```bash
curl -X POST http://127.0.0.1:8080/emu/rules \
  -H 'Content-Type: application/json' \
  -d @emu_rules/example_any_game.json
```

Or body: `{ "session": "x", "path": "example_any_game.json" }` / inline `"values": { ... }`.

Find addresses with a PS2 cheat engine / PCSX2 tools for the game you own; put them in JSON. Lloyd never needs the game name baked into code.

## Host duty

Your capture script (or future ARMSX2 plugin) each frame/second:

1. Screenshot / caption → `frame`
2. Optional audio note → `audio`
3. Read RAM (or expose values from emulator) → `values` / `mem`
4. Optional outcome → `reaction`
5. `POST /emu/tick`
6. `GET /emu/inputs` → apply pad to emulator

Lloyd experiences the **full loop inside his mind** every tick.
