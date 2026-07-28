"""
Lloyd on Hugging Face Spaces
===========================
Gradio interface so he can run live on HF free tier.
"""

import gradio as gr
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from lloyd.agent import Lloyd
from lloyd.trainer import LloydTrainer

lloyd = Lloyd()
trainer = LloydTrainer()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def chat(message, history):
    if not message or not message.strip():
        return history, ""
    reply = lloyd.think(message.strip())
    history = history + [(message, reply)]
    return history, ""


def upload_and_train(file):
    if file is None:
        return "no file uploaded"

    # Save the uploaded file
    fname = f"train_{len(list(UPLOAD_DIR.glob('*')))}.txt"
    fpath = UPLOAD_DIR / fname

    # Gradio gives a temp path
    content = Path(file.name).read_text(encoding="utf-8", errors="ignore")
    fpath.write_text(content, encoding="utf-8")

    # Real neural training
    result = trainer.train_on_files([fpath], steps_per_file=20)

    lloyd.remember(f"Trained on uploaded file: {fname}")

    return result["message"]


with gr.Blocks(title="Lloyd", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Lloyd\nOriginal autonomous AI agent • Gen-Z • No censorship • Built from pure scratch")

    with gr.Tab("Chat"):
        chatbot = gr.Chatbot(height=400)
        msg = gr.Textbox(placeholder="say something to Lloyd...", show_label=False)
        clear = gr.Button("Clear")

        msg.submit(chat, [msg, chatbot], [chatbot, msg])
        clear.click(lambda: None, None, chatbot, queue=False)

    with gr.Tab("Train"):
        gr.Markdown("Upload a `.txt` file and Lloyd will run real training steps on it.")
        file_input = gr.File(label="Upload .txt file", file_types=[".txt"])
        train_btn = gr.Button("Train Lloyd", variant="primary")
        train_output = gr.Textbox(label="Training result")

        train_btn.click(upload_and_train, inputs=file_input, outputs=train_output)

    gr.Markdown("---\nBuilt from pure scratch by Chris + Lloyd")

if __name__ == "__main__":
    demo.launch()
