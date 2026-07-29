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

## One Brain, Everywhere

Everything that makes Lloyd *Lloyd* lives in:

```
lloyd/          ← agent, personality, memory, trainer, english engine
model/          ← pure-NumPy Tiny Transformer (the actual neural net)
```

This is the **single source of truth**.  
Web, hosted server, and on-device APK all run the exact same code.

The brain is serializable:

- `trainer.save_brain("weights.npz")` / `load_brain(...)`
- `lloyd.export_brain("lloyd_brain.lloyd", trainer=trainer)` → one file with weights + memory
- UI has **Export** / **Import** buttons

Train him on your phone → export the `.lloyd` file → import on a server (or the other way around). Same weights, same memories.

---

## Current Status (v0.5)

- Pure NumPy Tiny Transformer with real learning  
- Upload `.txt` → Train → weights actually update  
- Auto-saves brain after every training run  
- Export / Import full brain as a single `.lloyd` file  
- Expanded English dictionary + Gen-Z slang  
- Autonomous agent with goals  
- Image generation placeholder  
- Vector memory  
- Local server + deployable Flask/WSGI version  
- Mobile web UI ready for on-device APK packaging  

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

## 2. Host the full version anywhere

| Platform          | How                                      |
|-------------------|------------------------------------------|
| Render / Railway  | `Procfile` → `python server.py`          |
| PythonAnywhere    | `flask_app.py` (WSGI)                    |
| Hugging Face      | `app.py` (Gradio)                        |
| Any VPS           | `python server.py` or gunicorn + flask   |

After training (or after importing a `.lloyd` file) the brain lives in the `brains/` folder and is restored on restart.

See `docs/BRAIN_TRANSFER.md` and `docs/DEPLOY.md`.

---

## 3. Full Lloyd inside an APK (train on the phone)

The Python brain is ready to run on-device.  
See **`docs/ON_DEVICE_APK.md`** for the two practical routes:

- **Chaquopy** — embed the existing Python code + WebView UI, local server on `127.0.0.1`
- **BeeWare / Briefcase** — pure Python APK

Either way you get real on-device training, and the **Export** button still gives you a `.lloyd` file you can move to a server later.

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
│   ├── english_engine.py
│   ├── memory.py
│   ├── personality.py
│   └── image_gen.py
├── model/
│   └── tiny_transformer.py   ← pure NumPy + save/load
├── interface/mobile_web/     ← UI (chat, train, export, import)
├── brains/                   ← auto-saved weights + memory (created at runtime)
├── docs/
│   ├── BRAIN_TRANSFER.md
│   ├── ON_DEVICE_APK.md
│   └── DEPLOY.md
└── requirements.txt
```

Built by Chris + Lloyd.
