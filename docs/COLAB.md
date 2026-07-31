# Host Lloyd on Google Colab (Chat + Image Generation)

One public link. Chat, draw, and train the 100 image patterns — all from Colab.

## 1. Open a new Colab notebook

Go to: https://colab.research.google.com → **New notebook**

## 2. Paste these cells

### Cell 1 — clone + install

```python
!git clone https://github.com/christhepimp/lloydchrisisai.git
%cd lloydchrisisai
!pip install -q gradio numpy
```

### Cell 2 — launch (gives you a public URL)

```python
!python app.py
```

Wait until you see something like:

```
Running on public URL: https://xxxx.gradio.live
```

Click that link. That’s Lloyd live.

## What’s inside the Colab UI

| Tab | What it does |
|-----|----------------|
| **Chat** | Talk to Lloyd. Type `draw uncanny valley doll face` and he returns a real PNG. |
| **Image Lab** | Direct image generation (bypasses chat router). |
| **Train Image Patterns** | Hardcodes the 100 pixel arrays and trains the pure-NumPy vision net. After this, chat + Image Lab get better. |
| **Train Text** | Upload a `.txt` and run real gradient steps on the chat transformer. |

## Optional: train images first (recommended)

In the **Train Image Patterns** tab:

- Epochs: `40` (or 60–100 if you have time)
- Hardcoded images: `100`
- Hit **Train Image Pattern Model**

When it finishes, Lloyd’s image model is live for the rest of the session.

## Mobile UI against Colab

If you still want the phone UI (`interface/mobile_web`):

1. Run Colab as above and copy the `https://xxxx.gradio.live` link  
   (Gradio is a different interface — for the exact mobile UI you need the raw `server.py` which Colab doesn’t expose as easily.)

**Best path on Colab = use `app.py` (Gradio).**  
It already has chat + image gen + train images + train text, all connected to the same Lloyd brain.

## One-liner version

```python
!git clone https://github.com/christhepimp/lloydchrisisai.git && cd lloydchrisisai && pip install -q gradio numpy && python app.py
```

Open the public Gradio URL it prints. Done.
