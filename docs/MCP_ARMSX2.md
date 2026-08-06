# Lloyd ↔ ARMSX2 via MCP

Lloyd connects to the running emulator through **MCP** (Model Context Protocol), not by embedding ARMSX2.

```
┌─────────┐  stdio MCP   ┌───────────┐   PINE IPC    ┌──────────────────┐
│  Lloyd  │ ───────────► │ mcp-pine  │ ────────────► │ ARMSX2 / PCSX2   │
│ agent   │              │ (Node)    │  slot 28011   │ PINE server on   │
└─────────┘              └───────────┘               └──────────────────┘
```

## What you need

1. **ARMSX2 or PCSX2** running with **PINE** enabled (PCSX2: Settings → Advanced → Enable PINE Server, slot **28011**).
2. **Node.js** (for `mcp-pine`) on the same machine / Termux.
3. **Lloyd** with MCP enabled in `secrets.json`.

> Android: PINE must be exposed by the build you use. Desktop PCSX2/ARMSX2 with PINE is the most reliable path today. If your Android ARMSX2 build has no PINE toggle, run the MCP path on a PC/Linux ARM box pointing at that emulator, or use Lloyd’s existing HTTP `/emu/*` bridge from the APK.

## Enable in Lloyd

Edit `secrets.json`:

```json
{
  "moltbook": "...",
  "mcp": {
    "enabled": true,
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "mcp-pine"],
    "env": {
      "PINE_TARGET": "pcsx2",
      "PINE_SLOT": "28011",
      "PINE_HOST": "127.0.0.1"
    }
  }
}
```

Or env:

```bash
export LLOYD_MCP_ENABLED=1
export PINE_SLOT=28011
python server.py
```

## Install mcp-pine (once)

```bash
npm install -g mcp-pine
# or use npx -y mcp-pine (default in config)
```

## HTTP API (Lloyd server)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/mcp/status` | Connection + tool list |
| POST | `/mcp/connect` | Start MCP session |
| POST | `/mcp/disconnect` | Stop |
| GET | `/mcp/tools` | List tools |
| POST | `/mcp/call` | `{ "name": "pine_ping", "arguments": {} }` |
| POST | `/mcp/sync` | Pull game info + RAM sample into `/emu` session |

### Examples

```bash
curl -X POST http://127.0.0.1:8080/mcp/connect
curl http://127.0.0.1:8080/mcp/status
curl -X POST http://127.0.0.1:8080/mcp/call \
  -H 'Content-Type: application/json' \
  -d '{"name":"pine_get_info","arguments":{}}'
curl -X POST http://127.0.0.1:8080/mcp/call \
  -H 'Content-Type: application/json' \
  -d '{"name":"pine_read32","arguments":{"address":1048576}}'
curl -X POST http://127.0.0.1:8080/mcp/sync \
  -H 'Content-Type: application/json' \
  -d '{"session":"default"}'
```

## Chat commands

| Say | Effect |
|-----|--------|
| `mcp status` | Show MCP connection |
| `mcp connect` | Connect to mcp-pine |
| `mcp tools` | List tools |
| `mcp ping` | `pine_ping` |
| `mcp info` | Game title / serial |
| `mcp sync` | Feed emu bridge from MCP |
| `mcp call <tool> [json args]` | Raw tool call |

## Tools from mcp-pine

- `pine_ping`, `pine_get_info`, `pine_get_status`
- `pine_read8/16/32/64`, `pine_read_range`
- `pine_write8/16/32/64`
- `pine_save_state`, `pine_load_state`

PINE does **not** expose controller injection or screenshots — for play actions keep using Lloyd `/emu/action` + host pad queue, or a future input MCP.

## Fork note

ARMSX2 fork with host helpers: https://github.com/christhepimp/ARMSX2 (branch `lloyd-api`).
