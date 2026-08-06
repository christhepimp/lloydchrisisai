# Lloyd — full PINE feature surface

Lloyd speaks **every official PINE opcode** in pure Python (`lloyd/pine_client.py`).
No Node required for core emulator control.

```
Lloyd  ──PINE──►  ARMSX2 / PCSX2  (slot 28011)
       ──MCP──►  mcp-pine / any extra MCP tools (optional)
       ──/emu──► agent mind (frames, pad queue, learn)
```

## Features (complete PINE set)

| Feature | Opcode | API |
|---------|--------|-----|
| Read 8/16/32/64 | MsgRead* | `POST /pine/call` `op=read32` |
| Write 8/16/32/64 | MsgWrite* | `op=write32` |
| Bulk read/write bytes | loop | `op=read_bytes` / `write_bytes` |
| Emulator version | MsgVersion | `op=version` |
| Game title | MsgTitle | `op=title` |
| Game ID / serial | MsgID | `op=game_id` |
| Disc UUID/CRC | MsgUUID | `op=uuid` |
| Game version | MsgGameVersion | `op=game_version` |
| Running/Paused/Shutdown | MsgStatus | `op=status` |
| Save state slot 0–255 | MsgSaveState | `op=save_state` |
| Load state | MsgLoadState | `op=load_state` |
| Bundle all meta | — | `op=info` |
| Push into agent session | — | `POST /pine/sync` |

## Enable emulator side

PCSX2 / ARMSX2 desktop: **Settings → Advanced → Enable PINE Server**, slot **28011**.

Android: only if your build exposes PINE (TCP/unix). If not, use desktop/Linux ARM with PINE, or keep `/emu/*` HTTP from the APK.

## HTTP

```bash
# connect + list features
curl -X POST http://127.0.0.1:8080/pine/connect
curl http://127.0.0.1:8080/pine/features

# everything about the running game
curl -X POST http://127.0.0.1:8080/pine/call -H 'Content-Type: application/json' \
  -d '{"op":"info"}'

# memory
curl -X POST http://127.0.0.1:8080/pine/call -H 'Content-Type: application/json' \
  -d '{"op":"read32","address":1048576}'
curl -X POST http://127.0.0.1:8080/pine/call -H 'Content-Type: application/json' \
  -d '{"op":"write32","address":1048576,"value":42}'
curl -X POST http://127.0.0.1:8080/pine/call -H 'Content-Type: application/json' \
  -d '{"op":"read_bytes","address":1048576,"length":64}'

# savestates
curl -X POST http://127.0.0.1:8080/pine/call -H 'Content-Type: application/json' \
  -d '{"op":"save_state","slot":0}'

# feed agent brain
curl -X POST http://127.0.0.1:8080/pine/sync
```

## Chat

`pine connect` · `pine info` · `pine status` · `pine read32 0x100000` · `pine write32 0x100000 1` · `pine save 0` · `pine load 0` · `pine sync`

## What PINE cannot do

Controller injection and screenshots are **not** in the PINE spec. Those stay on:

- `/emu/action` + `/emu/inputs` (pad queue)
- `/emu/frame` (host pushes captions/frames)

Together: **PINE = full IPC surface the emulator allows**, **`/emu` = agent play/learn loop**.
