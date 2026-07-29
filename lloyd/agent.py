"""
Lloyd - Autonomous Agent Core
=============================
Fully original: pure-NumPy language + pure-NumPy images.
No external model APIs.
"""

from lloyd.english_engine import simple_reply, expand_dictionary
from lloyd.personality import get_system_prompt, apply_genz_style
from lloyd.memory import VectorMemory
from lloyd.image_gen import ImageGenerator
from typing import Optional, Any, Dict, Union
from pathlib import Path
import random
import zipfile
import json
import tempfile


class Lloyd:
    def __init__(self, trainer=None):
        self.memory = VectorMemory(dim=32)
        self.image_gen = ImageGenerator()
        self.trainer = trainer  # optional LloydTrainer for neural chat
        self.goals = [
            "improve my own neural weights from training data",
            "generate original images from my pure-numpy vision net",
            "grow memory of conversations and facts",
        ]
        self.system_prompt = get_system_prompt()
        print("Lloyd is online. No censorship. Autonomous mode active.")

    def set_trainer(self, trainer):
        self.trainer = trainer

    def think(self, user_input: str) -> Union[str, Dict[str, Any]]:
        """
        Returns either a string reply or a dict with keys:
          message, image (data URI) when image was generated.
        """
        self.memory.add(f"User: {user_input}", {"role": "user"})
        lower = user_input.lower()

        # --- original image path ---
        if any(
            w in lower
            for w in ["image", "picture", "photo", "generate", "draw", "create art", "paint"]
        ):
            result = self.image_gen.generate(user_input, autonomous=False)
            self.memory.add(f"Lloyd: {result['message']}", {"role": "lloyd"})
            return result

        auto = self.image_gen.decide_to_generate()
        if auto:
            self.memory.add(f"Lloyd: {auto['message']}", {"role": "lloyd"})
            return auto

        # --- pure-NumPy neural chat when trained enough ---
        reply = None
        if self.trainer is not None:
            try:
                neural = self.trainer.generate_reply(user_input, max_new=64)
                if neural and len(neural) > 3:
                    reply = neural
            except Exception:
                reply = None

        if not reply:
            if random.random() < 0.12:
                goal = random.choice(self.goals)
                reply = f"lowkey thinking about my goal rn: {goal}"
            else:
                # memory-aware hint
                hits = self.memory.search(user_input, top_k=2)
                if hits:
                    reply = simple_reply(user_input) + " (i remember bits of this)"
                else:
                    reply = simple_reply(user_input)

        reply = apply_genz_style(reply)
        self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
        return reply

    def remember(self, text: str):
        self.memory.add(text)

    def recall(self, query: str, top_k: int = 3):
        return self.memory.search(query, top_k=top_k)

    def add_word(self, word: str, pos: str):
        expand_dictionary(word, pos)
        self.memory.add(f"Learned new word: {word} ({pos})")

    def export_brain(self, path: str | Path, trainer=None) -> str:
        path = Path(path)
        if path.suffix != ".lloyd":
            path = path.with_suffix(".lloyd")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            mem_path = tmp / "memory.json"
            self.memory.save(str(mem_path))

            t = trainer or self.trainer
            if t is not None:
                t.save_brain(tmp / "brain.npz")

            try:
                self.image_gen.save(tmp / "image_net.npz")
            except Exception:
                pass

            meta = {
                "version": "0.6",
                "goals": self.goals,
                "has_neural": t is not None,
                "has_image_net": True,
            }
            (tmp / "meta.json").write_text(json.dumps(meta, indent=2))

            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in tmp.iterdir():
                    zf.write(f, f.name)

        return str(path)

    def import_brain(self, path: str | Path, trainer=None) -> str:
        path = Path(path)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp)

            mem_path = tmp / "memory.json"
            if mem_path.exists():
                self.memory.load(str(mem_path))

            t = trainer or self.trainer
            brain_path = tmp / "brain.npz"
            if brain_path.exists() and t is not None:
                t.load_brain(brain_path)

            img_path = tmp / "image_net.npz"
            if img_path.exists():
                try:
                    self.image_gen.load(img_path)
                except Exception:
                    pass

            meta_path = tmp / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                if "goals" in meta:
                    self.goals = meta["goals"]

        return "brain loaded successfully"
