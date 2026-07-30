# Download Lloyd — Full Up-to-Date ZIP

Repo: **christhepimp/lloydchrisisai**

GitHub always builds a full source zip from the latest `main` branch.
Every file we added (importance, equals, reward, reflection, training loop, etc.) is included.

## Direct download (always current)

**→ [lloydchrisisai-main.zip](https://github.com/christhepimp/lloydchrisisai/archive/refs/heads/main.zip)**

Alternate API link:

**→ [zipball/main](https://api.github.com/repos/christhepimp/lloydchrisisai/zipball/main)**

## From the website

1. Open https://github.com/christhepimp/lloydchrisisai  
2. Click green **Code**  
3. Click **Download ZIP**

## What is inside (current stack)

- `lloyd/agent.py` — main agent  
- `lloyd/importance.py` — equals rule + ∆importance∆ + math  
- `lloyd/reward.py` — positive-only rewards  
- `lloyd/reflection.py` — self-reflection on wrong answers  
- `lloyd/training_loop.py` — interactive training (free answers → pattern questions)  
- `lloyd/memory.py`, `english_engine.py`, `personality.py`, `image_gen.py`, `trainer.py`, `tasks.py`  
- `model/tiny_transformer.py` — pure NumPy transformer  
- `lessons/` — lesson text files  
- `server.py`, `flask_app.py`, `main.py`, mobile UI, docs  

## After download

```bash
unzip lloydchrisisai-main.zip
cd lloydchrisisai-main
pip install -r requirements.txt
python server.py
```

Then in chat type:

```text
start training
```

That runs the live pattern loop (free answers first, then pattern transfer, reflection on wrong, reward on correct).

---
Share this zip with another AI — it is the full current brain of Lloyd.
