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
- **Fully portable brain** — train anywhere, move him later  
- **APK with no Android Studio** — built in the cloud by GitHub Actions  

## One Brain, Everywhere

Everything that makes Lloyd *Lloyd* lives in:

```
lloyd/          ← agent, personality, memory, trainer, english engine
model/          ← pure-NumPy Tiny Transformer (the actual neural net)
```

This is the **single source of truth**.  
Web, hosted server, and APK all use the exact same brain.

The brain is serializable:

- `trainer.save_brain("weights.npz")` / `load_brain(...)`
- `lloyd.export_brain("lloyd_brain.lloyd", trainer=trainer)` → one file with weights + memory
- UI has **Export** / **Import** buttons

Train him → export the `.lloyd` file → import on any other Lloyd instance. Same weights, same memories.

---

## Get the APK (no Android Studio)

1. Open **Actions** on this repo  
2. Choose **Build Lloyd APK** → **Run workflow**  
3. Wait for the green check → download the **lloyd-apk** artifact  
4. Install `app-debug.apk` on your phone (allow unknown sources)  

Full steps: **[`docs/GET_THE_APK.md`](docs/GET_THE_APK.md)**

In the app, tap **⚙** and paste the URL of your hosted Lloyd (Render / Railway / etc.) so chat + train + export all work from the phone.

---

## 1. Run the full version locally

```bash
pip install -r requirements.txt
python server.py
```

Open **http://localhost:8080**

1. Chat with Lloyd  
2. **Upload** a `.txt` → **Train** (real gradient steps)  
3. **Export** → download `lloyd_brain.lloyd`  
4. Later **Import** that file on any other Lloyd instance  

---

## 2. Host the full version anywhere (for the APK to talk to)

| Platform          | How                                      |
|-------------------|------------------------------------------|
| Render / Railway  | `Procfile` → `python server.py`          |
| PythonAnywhere    | `flask_app.py` (WSGI)                    |
| Hugging Face      | `app.py` (Gradio)                        |
| Any VPS           | `python server.py` or gunicorn + flask   |

After training (or after importing a `.lloyd` file) the brain lives in the `brains/` folder and is restored on restart.

See `docs/BRAIN_TRANSFER.md` and `docs/DEPLOY.md`.

---

## 3. True offline on-device brain (later)

When you want training to run *inside* the phone with no server, see **`docs/ON_DEVICE_APK.md`** (Chaquopy / BeeWare). The portable `.lloyd` format already works for moving that brain anywhere.

---

## Project Structure

```
lloydchrisisai/
├── server.py                 ← local + most cloud hosts
├── flask_app.py              ← PythonAnywhere / WSGI
├── app.py                    ← Hugging Face Gradio
├── lloyd/                    ← THE BRAIN
│   ├── agent.py              ← export_brain / import_brain
│   ├── trainer.py            ← save_brain / load_brain
│   └── ...
├── model/
│   └── tiny_transformer.py   ← pure NumPy + save/load
├── interface/mobile_web/     ← UI (chat, train, export, import, ⚙)
├── .github/workflows/
│   └── build-apk.yml         ← cloud APK build (no Android Studio)
├── docs/
│   ├── GET_THE_APK.md
│   ├── BRAIN_TRANSFER.md
│   ├── ON_DEVICE_APK.md
│   └── DEPLOY.md
└── requirements.txt
```

Built by Chris + Lloyd.
