# Lloyd TextFiction — Autonomous Z-Machine Player

Fork base: **onyxbits/TextFiction 2.7** (Apache-2.0)  
Same app as `text-fiction-2-7.apk`, plus an embedded agent API so **Lloyd plays the whole game**.

## Agent API (on the phone, port 8765)

| Method | Path | Action |
|--------|------|--------|
| GET | `/status` | Health |
| GET | `/state` | `{ "text", "status_line", "waiting_for_command" }` |
| POST | `/command` | Body: `look` or `{"command":"look"}` — submits to Z-machine |
| POST | `/reset` | Clear buffers |

## What was changed in source

1. **Added** `src/de/onyxbits/textfiction/lloyd/LloydAgentApi.java`
2. **Patched** `GameActivity.java`
   - starts API in `onCreate`
   - `publishResult()` → pushes story text to `/state`
   - command sink → `executeCommand()`
   - stops API in `onDestroy`
3. **Manifest** — `INTERNET` + `ACCESS_NETWORK_STATE`

## Build the APK

```bash
git clone https://github.com/onyxbits/TextFiction.git
cd TextFiction
# copy lloyd/ LloydAgentApi.java + patched GameActivity.java from this folder
# ensure INTERNET in AndroidManifest.xml
# Import into Android Studio → Build APK → sign → install
```

## Play loop

```bash
curl http://PHONE_IP:8765/state
curl -X POST http://PHONE_IP:8765/command -d 'look'
python lloyd_play_client.py --base http://PHONE_IP:8765
```

Import any `.z5` story; Lloyd can play the full run via the API.
