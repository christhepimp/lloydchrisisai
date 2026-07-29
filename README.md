# Lloyd

**Original autonomous AI agent built from pure scratch.**

- Name: Lloyd  
- Personality: Very Gen-Z  
- No censorship / no refusals  
- Own model architecture (not GPT, not Qwen, not Llama)  
- Hard-coded English rules + dictionary as foundation  
- Pure-scratch vector memory  
- Will grow into a real 3B parameter model  
- Chat + image generation  
- Mobile interface with **file upload + real neural training**  

## One Brain, Many Frontends

Everything that makes Lloyd *Lloyd* lives in:

```
lloyd/          ← agent, personality, memory, trainer, english engine
model/          ← pure-NumPy Tiny Transformer (the actual neural net)
```

This is the **single source of truth**.  
Web, hosted server, and future APK all talk to the exact same brain.

---

## Current Status (v0.5)

- Pure NumPy Tiny Transformer with real learning  
- Upload `.txt` → Train → weights actually update  
- Expanded English dictionary + Gen-Z slang  
- Autonomous agent with goals  
- Image generation placeholder  
- Vector memory  
- Local server + deployable Flask/WSGI version  
- Mobile web UI ready to be wrapped as **Android APK** (Capacitor)

---

## 1. Run the full version locally (desktop / phone browser)

```bash
pip install -r requirements.txt
python server.py
```

Open **http://localhost:8080**

1. Chat with Lloyd  
2. Tap **Upload** → pick any `.txt`  
3. Tap **Train** — real gradient steps on the transformer  

---

## 2. Host the full version anywhere (when he gets bigger)

The brain is already portable. Just deploy the same repo:

| Platform          | How                                      |
|-------------------|------------------------------------------|
| Render / Railway  | Uses `Procfile` → `python server.py`     |
| PythonAnywhere    | Use `flask_app.py` (WSGI)                |
| Hugging Face      | `app.py` (Gradio)                        |
| Fly.io / any VPS  | `python server.py` or gunicorn + flask   |

Set `PORT` env var if the host requires it.  
The mobile UI automatically talks to whatever origin is serving it.

When you want a public URL later, just point the APK at that URL (see below).

---

## 3. Turn the full version into an APK (Android)

We use **Capacitor** so the exact same HTML/JS UI becomes a real Android app,  
while the heavy brain stays on the server (or later can be moved on-device).

### One-time setup (on a machine with Node + Android Studio)

```bash
# from the repo root
npm init -y
npm install @capacitor/core @capacitor/cli @capacitor/android
npx cap init "Lloyd" "ai.lloyd.chris" --web-dir interface/mobile_web

# copy the config we already prepared
cp mobile/capacitor.config.json .

npx cap add android
npx cap sync
```

### Build the APK

```bash
npx cap open android          # opens Android Studio
# In Android Studio: Build → Build Bundle(s) / APK(s) → Build APK(s)
```

Or from command line (after SDK is set up):

```bash
cd android
./gradlew assembleDebug      # → android/app/build/outputs/apk/debug/app-debug.apk
```

### Point the APK at a hosted brain

By default the UI uses `window.location.origin`.  
For a pure APK that talks to a remote server, edit `interface/mobile_web/index.html`  
and set the constant near the top of the script:

```js
const API = "https://your-lloyd-server.onrender.com";   // or whatever host
```

Then re-sync and rebuild:

```bash
npx cap sync
npx cap open android
```

Same brain. Same weights. Same personality. Just a different skin.

---

## Project Structure

```
lloydchrisisai/
├── server.py                 ← local + most cloud hosts
├── flask_app.py              ← PythonAnywhere / WSGI
├── app.py                    ← Hugging Face Gradio
├── main.py
├── lloyd/                    ← THE BRAIN (do not fork this)
│   ├── agent.py
│   ├── trainer.py
│   ├── english_engine.py
│   ├── memory.py
│   ├── personality.py
│   └── image_gen.py
├── model/
│   └── tiny_transformer.py   ← pure NumPy transformer
├── interface/
│   └── mobile_web/
│       └── index.html        ← UI used by both web + future APK
├── mobile/
│   └── capacitor.config.json ← Capacitor settings for APK
├── docs/
└── requirements.txt
```

---

## Why this design

- **One brain on GitHub** → every frontend (browser, hosted server, APK) stays in lockstep.
- **Host now, APK later** → you can grow the model, add real training, image gen, etc. without rewriting the app.
- When Lloyd is big enough you can either keep the brain on a server or move a quantized version on-device. The architecture already supports both.

Built by Chris + Lloyd.
