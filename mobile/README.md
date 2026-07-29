# Building the Lloyd APK

**Same brain.** The APK is only a shell.  
All intelligence stays in `lloyd/` + `model/` on GitHub (and whatever server you deploy).

## Prerequisites

- Node.js 18+
- Android Studio (Android SDK + Java 17)

## One-time setup (from repo root)

```bash
npm install
cp mobile/capacitor.config.json .
npx cap add android
npx cap sync
```

Or the single script:

```bash
npm run apk:setup
```

## Build the APK

```bash
npm run apk:open
# Android Studio → Build → Build Bundle(s) / APK(s) → Build APK(s)
# Output: android/app/build/outputs/apk/debug/app-debug.apk
```

Command-line alternative (after SDK is configured):

```bash
cd android
./gradlew assembleDebug
```

## Point the APK at a hosted brain (when you deploy later)

1. Host the full version (see `docs/DEPLOY.md` or root README).
2. Edit `interface/mobile_web/index.html` and change:

```js
const API = window.location.origin;
```

to:

```js
const API = "https://YOUR-LLOYD-URL.onrender.com";  // or Railway, Fly, etc.
```

3. Re-sync and rebuild:

```bash
npm run apk:sync
npm run apk:open
```

Same weights. Same personality. Same training. Different skin.

When Lloyd is big enough you can later ship an on-device quantized brain — the UI already talks over HTTP so nothing has to be rewritten.
