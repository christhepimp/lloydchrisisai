"""
Lloyd — Gradio App (Chat + Image Generation)
=============================================
Works on Hugging Face Spaces and Google Colab.
Pure-NumPy brain + pure-NumPy image pattern model.
"""

from __future__ import annotations

import gradio as gr
from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).parent))

from lloyd.agent import Lloyd
from lloyd.trainer import LloydTrainer

# ---------------------------------------------------------------------------
# Boot Lloyd
# ---------------------------------------------------------------------------
trainer = LloydTrainer()
lloyd = Lloyd(trainer=trainer)

# Try to load image pattern weights if they already exist
try:
    from model.image_pattern_learner import ImagePatternLearner
    pattern = ImagePatternLearner()
    weights = Path("image_pattern.npz")
    if weights.exists():
        pattern.load(weights)
        lloyd.image_gen.pattern = pattern
        lloyd.image_gen.net = pattern.net
        print("Loaded trained image_pattern.npz")
    else:
        # still attach the learner so training can happen later
        lloyd.image_gen.pattern = pattern
        print("Image pattern learner ready (not trained yet)")
except Exception as e:
    print("Image pattern learner not available:", e)
    pattern = None


def _format_reply(result):
    """Turn Lloyd's reply into Gradio chatbot format (text + optional image)."""
    if isinstance(result, dict):
        text = result.get("message") or result.get("reply") or ""
        img = result.get("image")
        if img:
            # Gradio chatbot accepts (text, image) tuples in newer versions;
            # we return text and let the image component handle display.
            return text, img
        return text, None
    return str(result), None


def chat(message, history):
    if not message or not str(message).strip():
        return history, ""
    try:
        result = lloyd.think(str(message).strip())
        text, img = _format_reply(result)
        # history is list of [user, assistant]
        # For image we append the data-uri so Gradio can show it
        if img:
            # Gradio 4+ Chatbot can take HTML or we show image below
            assistant_msg = f"{text}\n\n![lloyd]({img})"
        else:
            assistant_msg = text
        history = history + [[message, assistant_msg]]
        return history, ""
    except Exception as e:
        err = f"error: {e}\n{traceback.format_exc()}"
        history = history + [[message, err]]
        return history, ""


def train_image_patterns(epochs, n_images, progress=gr.Progress()):
    """Hardcode N pixel arrays and train the image pattern model."""
    try:
        from model.image_pattern_learner import ImagePatternLearner
        learner = ImagePatternLearner()
        progress(0, desc="Loading hardcoded pixel arrays...")
        n = learner.load_hardcoded_images(n=int(n_images))
        progress(0.1, desc=f"Stored {n} images — training...")

        # simple progress callback via print + occasional update
        def _train():
            return learner.train(epochs=int(epochs), lr=0.015, log_every=max(1, int(epochs)//10))

        result = _train()
        learner.save("image_pattern.npz")

        # hot-swap into live Lloyd
        lloyd.image_gen.pattern = learner
        lloyd.image_gen.net = learner.net

        return (
            f"Done.\n"
            f"Images hardcoded: {result['images']}\n"
            f"Epochs: {result['epochs']}\n"
            f"Loss: {result['start_loss']:.4f} → {result['final_loss']:.4f}\n"
            f"Saved → image_pattern.npz\n"
            f"Lloyd image model is now live."
        )
    except Exception as e:
        return f"Training failed:\n{traceback.format_exc()}"


def generate_direct(prompt):
    """Direct image generation (bypasses chat router)."""
    try:
        result = lloyd.image_gen.generate(prompt or "uncanny valley doll face")
        img = result.get("image")
        msg = result.get("message", "")
        return img, msg
    except Exception as e:
        return None, f"error: {e}"


def upload_and_train_text(file):
    if file is None:
        return "no file uploaded"
    try:
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        fname = f"train_{len(list(upload_dir.glob('*')))}.txt"
        fpath = upload_dir / fname
        content = Path(file.name).read_text(encoding="utf-8", errors="ignore")
        fpath.write_text(content, encoding="utf-8")
        result = trainer.train_on_files([fpath], steps_per_file=30)
        lloyd.remember(f"Trained on uploaded file: {fname}")
        return result["message"]
    except Exception as e:
        return f"error: {e}"


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
with gr.Blocks(title="Lloyd", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # Lloyd
        **Original autonomous AI** • pure-NumPy chat + pure-NumPy image generation  
        No external image APIs. Uncanny-valley / pattern learning model included.
        """
    )

    with gr.Tab("Chat"):
        chatbot = gr.Chatbot(
            height=480,
            label="Lloyd",
            avatar_images=(None, None),
            render_markdown=True,
        )
        with gr.Row():
            msg = gr.Textbox(
                placeholder="say something… or try: draw uncanny valley doll face",
                show_label=False,
                scale=5,
            )
            send_btn = gr.Button("Send", variant="primary", scale=1)
        clear = gr.Button("Clear chat")

        def user_submit(message, history):
            return chat(message, history)

        msg.submit(user_submit, [msg, chatbot], [chatbot, msg])
        send_btn.click(user_submit, [msg, chatbot], [chatbot, msg])
        clear.click(lambda: [], None, chatbot, queue=False)

        gr.Examples(
            examples=[
                "yo lloyd",
                "draw an uncanny valley doll face",
                "draw creepy porcelain skin",
                "draw abstract purple vibes",
                "draw a robot face like lloyd",
                "who are you",
            ],
            inputs=msg,
        )

    with gr.Tab("Image Lab"):
        gr.Markdown("Direct image generation from the pure-NumPy pattern model.")
        img_prompt = gr.Textbox(label="Prompt", value="uncanny valley doll face")
        img_btn = gr.Button("Generate", variant="primary")
        img_out = gr.Image(label="Lloyd pixels", type="filepath")
        img_msg = gr.Textbox(label="Status")

        def _gen(p):
            data_uri, status = generate_direct(p)
            if data_uri is None:
                return None, status
            # Gradio Image wants a file path or numpy; convert data-uri → temp file
            import base64, tempfile
            header, b64 = data_uri.split(",", 1)
            raw = base64.b64decode(b64)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(raw)
            tmp.close()
            return tmp.name, status

        img_btn.click(_gen, inputs=img_prompt, outputs=[img_out, img_msg])

    with gr.Tab("Train Image Patterns"):
        gr.Markdown(
            """
            Hardcodes **N** synthetic uncanny-valley / pattern images as exact pixel arrays,  
            then trains the pure-NumPy vision net for the chosen number of epochs.  
            After training, chat + Image Lab use the improved model automatically.
            """
        )
        with gr.Row():
            ep = gr.Slider(5, 150, value=40, step=5, label="Epochs")
            nimg = gr.Slider(20, 100, value=100, step=10, label="Hardcoded images")
        train_img_btn = gr.Button("Train Image Pattern Model", variant="primary")
        train_img_out = gr.Textbox(label="Training log", lines=8)
        train_img_btn.click(train_image_patterns, inputs=[ep, nimg], outputs=train_img_out)

    with gr.Tab("Train Text"):
        gr.Markdown("Upload a `.txt` file — Lloyd runs real gradient steps on it.")
        file_input = gr.File(label="Upload .txt", file_types=[".txt"])
        train_txt_btn = gr.Button("Train on text", variant="primary")
        train_txt_out = gr.Textbox(label="Result")
        train_txt_btn.click(upload_and_train_text, inputs=file_input, outputs=train_txt_out)

    gr.Markdown("---\nBuilt from pure scratch • Chat + Image Pattern Learning")

if __name__ == "__main__":
    # share=True gives a public link — perfect for Colab
    demo.queue().launch(share=True, debug=True)
