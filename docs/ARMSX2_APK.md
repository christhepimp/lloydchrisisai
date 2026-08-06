# Lloyd APK + ARMSX2 (PS2) API settings

## What you get

| App | Role |
|-----|------|
| **Lloyd APK** (this repo, Capacitor) | Brain + **API settings inside the app** (session, game, goal, play/learn) |
| **ARMSX2** (upstream) | Actual PS2 emulator — install from [ARMSX2 releases](https://github.com/ARMSX2/ARMSX2/releases) |
| **Host bridge** (Termux / Python) | Optional: push frames + drain `/emu/inputs` while you play |

We do **not** rebuild ARMSX2. It is a large GPL-3.0 PCSX2 fork (NDK/CMake). Lloyd stays a thin HTTP agent the same way a crypto bot would talk to an exchange API.

## API settings live inside Lloyd

Open the Lloyd APK → **PS2** button (or Settings):

- **Lloyd server URL** — e.g. `http://127.0.0.1:8080` (Termux) or your hosted brain
- **Session ID** — e.g. `gt4`
- **Game name** — e.g. `Gran Turismo 4`
- **Goal** — what Lloyd should try to do
- **Push caption** — describe what is on screen → feeds `/emu/frame` → memory
- **Play** — Lloyd decides + queues DualShock action (`/emu/play`)
- **Learn** — trajectory into brain (`/emu/learn`)
- **Status / Inputs** — bridge health + pending controller queue

Same brain path as chat, vision, audio, Moltbook, or a crypto API feed.

## Build the Lloyd APK (Capacitor — not a full Gradle emulator port)

From repo root (needs Node 18+, Android Studio / SDK):

```bash
npm install
cp mobile/capacitor.config.json .
npx cap add android   # first time only
npx cap sync
npx cap open android
# Android Studio → Build → Build APK(s)
# Output: android/app/build/outputs/apk/debug/app-debug.apk
```

Or after SDK is set up:

```bash
cd android && ./gradlew assembleDebug
```

Install the APK on the same phone as ARMSX2 (or any device that can reach your Lloyd server).

## On-device stack (recommended)

1. **Termux** (or hosted server): `python server.py` → Lloyd mind on port 8080  
2. **Lloyd APK**: set server URL to `http://PHONE_IP:8080` (or localhost if using a local tunnel)  
3. **ARMSX2**: play as normal with your own BIOS + legal dumps  
4. While playing: in Lloyd APK use **Push caption** / **Play** / **Learn**, or run `armsx2-lloyd/host_stub.py` in Termux

### Termux host stub

```bash
cd ~/lloydchrisisai   # or your clone
python armsx2-lloyd/host_stub.py
```

Edit `BASE` in the stub if needed. Poll `/emu/inputs` and apply buttons manually or with ADB/accessibility later.

## Why not put the API inside ARMSX2 itself?

- No public plugin/HTTP surface for external agents today
- Forking + NDK build is the same class of pain as the old TextFiction Gradle failures
- Lloyd’s job is the **agent API** (observe → decide → act → learn). Stock ARMSX2 already renders and takes pad input

Future option: AccessibilityService companion or ARMSX2 plugin if upstream adds one. The HTTP contract (`/emu/*`) stays the same.

## Legal

- Your own PS2 BIOS
- Legally obtained game dumps
- Lloyd never ships BIOS/ISOs
