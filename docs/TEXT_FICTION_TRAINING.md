# Text Fiction APK ↔ Lloyd Training

## What this is
`text-fiction-2-7.apk` is a classic interactive-fiction (IF) Android client.
Lloyd does **not** need the APK source rewritten. He connects through his HTTP agent API and learns every room, choice, and command.

## API (agent mind — direct)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chat` | Straight to Lloyd's mind (`lloyd.think`) |
| POST | `/vision` | Image + caption → memory + optional train |
| POST | `/audio` | Speech transcript → mind |
| POST | `/textfiction/observe` | Send room text / choices / player command |
| POST | `/textfiction/suggest` | Lloyd picks next IF command |
| POST | `/textfiction/learn` | Train on the whole session story |
| GET  | `/textfiction/status` | Session stats |
| GET  | `/status` | Agent + vision + audio health |

### Example — observe a turn
```bash
curl -X POST http://HOST:8080/textfiction/observe \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "play1",
    "room_text": "You are in a dusty library. A book glows on the table.",
    "choices": ["read book", "go north", "look"],
    "command": "look"
  }'
```

### Example — Lloyd suggests next move
```bash
curl -X POST http://HOST:8080/textfiction/suggest \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "play1"}'
```

### Example — learn everything from the session
```bash
curl -X POST http://HOST:8080/textfiction/learn \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "play1", "steps": 30}'
```

## Vision
```bash
curl -X POST http://HOST:8080/vision \
  -H 'Content-Type: application/json' \
  -d '{"caption": "uncanny doll face on screen", "image_b64": "<optional base64>", "learn": true}'
```

## Audio
Client does STT; send the transcript:
```bash
curl -X POST http://HOST:8080/audio \
  -H 'Content-Type: application/json' \
  -d '{"transcript": "go north and open the door"}'
```

## APK readiness (sign + install)

1. The file `text-fiction-2-7.apk` is the original signed package (already has META-INF certs).
2. For **debug install** on your phone: enable unknown sources → install as-is.
3. For **release re-sign** (your own key):
   ```bash
   zipalign -v -p 4 text-fiction-2-7.apk text-fiction-aligned.apk
   apksigner sign --ks your.keystore --out text-fiction-signed.apk text-fiction-aligned.apk
   apksigner verify text-fiction-signed.apk
   ```
4. Play the game. While playing (or via a small bridge/script), POST room text + commands to `/textfiction/observe`.
5. When a chapter ends, call `/textfiction/learn` so Lloyd trains on the full story log.

## How Lloyd learns from it
- Every observe → memory write
- learn → builds a lesson `.txt` from rooms/choices/commands and runs real gradient steps
- suggest → agent mind picks the next command (play loop)

No external LLM. Pure Lloyd agent path.
