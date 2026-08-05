# Lloyd TextFiction Fork

**Base:** official [onyxbits/TextFiction](https://github.com/onyxbits/TextFiction) v2.7 (Apache-2.0)  
**Same app as** `text-fiction-2-7.apk` — Z-Machine player (Zork etc.), not a single story.

## Why this path (not decompile)

| Approach | Result |
|----------|--------|
| Decompile closed APK | Broken smali, not real source, legal risk for proprietary apps |
| **Official TextFiction source** | Clean Java, same as your APK, legal to fork under Apache-2.0 |

Closed commercial apps: decompile ≠ full original source. TextFiction is open; we start from real source.

## What we add

`LloydAgentApi` — embedded HTTP server on **port 8765**:

| Method | Path | Purpose |
|--------|------|--------|
| GET | `/status` | Agent API alive |
| GET | `/state` | Current story text + status line + waiting flag |
| POST | `/command` | Lloyd submits a player command (controls the game) |
| POST | `/reset` | Clear buffers |

Lloyd plays the **whole** story: loop `GET /state` → decide → `POST /command` until finished.

## Wire into GameActivity

1. Field: `private LloydAgentApi lloydApi;`
2. In `onCreate` after engine ready — start API and sink commands into `executeCommand`.
3. End of `publishResult()` — `lloydApi.publishState(text, status, waiting)`.
4. Manifest: `INTERNET` permission.
5. Optional package rename `ai.lloyd.textfiction` for side-by-side install.

## Build

1. Clone https://github.com/onyxbits/TextFiction
2. Add `LloydAgentApi.java` (see `src/.../lloyd/LloydAgentApi.java` in this folder)
3. Hook GameActivity as above
4. Build APK in Android Studio / Gradle → sign → install

## Lloyd autonomy

```text
GET  http://PHONE_IP:8765/state
POST http://PHONE_IP:8765/command   body: look
```

Import any `.z5` story into the library; Lloyd plays whatever is loaded.
