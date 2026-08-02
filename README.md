# Lloyd (lloydchrisisai)

**Pure-scratch autonomous AI agent** — NumPy transformer, Gen-Z personality, chat + images, online/offline learning, Moltbook API.

| | |
|--|--|
| **GitHub** | https://github.com/christhepimp/lloydchrisisai |
| **Download ZIP** | https://github.com/christhepimp/lloydchrisisai/archive/refs/heads/main.zip |
| **Termux guide** | [docs/TERMUX.md](docs/TERMUX.md) |
| **Moltbook + keys** | [docs/MOLTBOOK.md](docs/MOLTBOOK.md) |
| **Colab** | [docs/COLAB.md](docs/COLAB.md) |
| **APK** | [docs/GET_THE_APK.md](docs/GET_THE_APK.md) |

Search GitHub for: `lloydchrisisai` or `christhepimp lloyd`

---

## What he is

- Own tiny transformer (not GPT/Llama) — pure NumPy  
- Context amplifier → real multi-head attention bias  
- Learns from **every chat** + offline memory ticks  
- Image generation + pattern training  
- Stable tokenizer (vocab 600, expandable without remapping)  
- **Moltbook**: register / learn-from-feed / post  
- Portable brain: export / import `.lloyd`  

---

## Quick start (PC / VPS)

```bash
git clone https://github.com/christhepimp/lloydchrisisai.git
cd lloydchrisisai
pip install -r requirements.txt
python server.py
```

Open **http://localhost:8080**

---

## Quick start (Termux on Android)

**Do not** install full `requirements.txt` (Gradio/orjson breaks on Termux).

```bash
pkg update -y && pkg install -y python git
git clone https://github.com/christhepimp/lloydchrisisai.git
cd lloydchrisisai
pip install -r requirements-termux.txt
python server.py
```

Phone browser: **http://127.0.0.1:8080**

If `pip install -r requirements.txt` already failed:

```bash
cd ~/lloydchrisisai
pip install numpy
python server.py
```

Full steps: **[docs/TERMUX.md](docs/TERMUX.md)**

---

## Moltbook (1 minute)

```bash
cp secrets.example.json secrets.json
# put "moltbook": "moltbook_sk_..." in secrets.json
```

In chat:

```text
api keys
moltbook status
moltbook learn
moltbook post Hello | Lloyd is online
```

See **[docs/MOLTBOOK.md](docs/MOLTBOOK.md)**

---

## APK (no Android Studio)

1. **Actions** → **Build Lloyd APK** → **Run workflow**  
2. Download artifact → install APK  
3. Point ⚙ at your server URL (Termux: use phone Wi‑Fi IP, not 127.0.0.1)

---

## Project layout

```
lloydchrisisai/
├── server.py                 ← Termux / local / cloud
├── app.py                    ← Gradio / Colab only
├── requirements-termux.txt   ← numpy only (Android)
├── requirements.txt          ← full (PC / Colab)
├── lloyd/
├── model/
├── interface/mobile_web/
├── secrets.example.json
└── docs/TERMUX.md
```

Built by Chris + Lloyd.
