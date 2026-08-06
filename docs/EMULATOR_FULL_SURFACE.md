# Every emulator feature Lloyd can use

## 1. Full PINE IPC (pure Python — no Node)

Module: `lloyd/pine_client.py`  
HTTP: `/pine/*`  
Chat: `pine …`

| Emulator capability | Lloyd |
|---------------------|-------|
| Read memory 8/16/32/64 | yes |
| Write memory 8/16/32/64 | yes |
| Bulk read/write bytes | yes |
| Emulator version | yes |
| Game title | yes |
| Game ID / serial | yes |
| UUID / disc CRC | yes |
| Game version string | yes |
| Status Running/Paused/Shutdown | yes |
| Save state 0–255 | yes |
| Load state 0–255 | yes |

That is **100% of the official PINE opcode set** PCSX2/ARMSX2 exposes over IPC.

## 2. Optional MCP (extra tools)

`/mcp/*` + `mcp-pine` or any MCP server — for tools beyond PINE if you attach PCSX2-MCP DebugServer etc.

## 3. Agent play/learn loop (`/emu/*`)

Not in PINE (by design of the protocol):

| Need | Lloyd path |
|------|------------|
| Vision / captions | `/emu/frame` |
| Audio | `/emu/audio` |
| Pad queue | `/emu/action` → `/emu/inputs` |
| Decide / play | `/emu/decide` `/emu/play` |
| Rules + rewards | `/emu/rules` `/emu/reaction` `/emu/tick` |
| Learn | `/emu/learn` |

## Enable PINE on the emulator

Settings → Advanced → **Enable PINE Server** → slot **28011**.

```bash
curl -X POST http://127.0.0.1:8080/pine/connect
curl -X POST http://127.0.0.1:8080/pine/call -H 'Content-Type: application/json' -d '{"op":"info"}'
```

Docs: [PINE_FULL.md](PINE_FULL.md) · [MCP_ARMSX2.md](MCP_ARMSX2.md)
