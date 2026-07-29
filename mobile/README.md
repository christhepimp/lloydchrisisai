# Building the Lloyd APK

This folder contains the Capacitor config that turns the existing mobile web UI into a real Android app.

The **brain stays the same** (`lloyd/` + `model/`). The APK is just a shell that talks to whatever server is running that brain.

## Prerequisites

- Node.js 18+
- Android Studio (with Android SDK)
- Java 17

## Steps

From the **repo root**:

```bash
npm init -y
npm install @capacitor/core @capacitor/cli @capacitor/android

# Use the config we already committed
cp mobile/capacitor.config.json .

npx cap init "Lloyd" "ai.lloyd.chris" --web-dir interface/mobile_web
npx cap add android
npx cap sync
npx cap open android
```

In Android Studio:

1. Let Gradle finish syncing
2. Build → Build Bundle(s) / APK(s) → Build APK(s)
3. Find the APK under `android/app/build/outputs/apk/debug/`

## Pointing the APK at a hosted Lloyd

Edit `interface/mobile_web/index.html` and change:

```js
const API = window.location.origin;
```

to:

```js
const API = "https://YOUR-DEPLOYED-LLOYD-URL";
```

Then:

```bash
npx cap sync
npx cap open android
```

and rebuild.

Same brain. Same training. Same personality.
