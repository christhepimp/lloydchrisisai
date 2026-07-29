"""
Lloyd - Autonomous Agent Core
=============================
This is the brain that decides what to do.
Fully portable: export_brain() / import_brain() move everything.
"""

from lloyd.english_engine import simple_reply, expand_dictionary
from lloyd.personality import get_system_prompt, apply_genz_style
from lloyd.memory import VectorMemory
from lloyd.image_gen import ImageGenerator
from typing import Optional
from pathlib import Path
import random
import zipfile
import json
import tempfile
import os


class Lloyd:
    def __init__(self):
        self.memory = VectorMemory(dim=32)
        self.image_gen = ImageGenerator()
        self.goals = [
            "improve my english dictionary and grammar rules",
            "generate images when i feel creative",
            "grow my personal memory of conversations and facts",
        ]
        self.system_prompt = get_system_prompt()
        print("Lloyd is online. No censorship. Autonomous mode active.")

    def think(self, user_input: str) -> str:
        self.memory.add(f"User: {user_input}", {"role": "user"})

        lower = user_input.lower()

        if any(w in lower for w in ["image", "picture", "photo", "generate", "draw", "create art"]):
            prompt = user_input
            reply = self.image_gen.generate(prompt, autonomous=False)
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        auto_img = self.image_gen.decide_to_generate()
        if auto_img:
            self.memory.add(f"Lloyd: {auto_img}", {"role": "lloyd"})
            return auto_img

        if random.random() < 0.12:
            goal = random.choice(self.goals)
            reply = f"lowkey thinking about my goal rn: {goal}"
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

    # ------------------------------------------------------------------
    # FULL BRAIN TRANSFER
    # Packs neural weights + vector memory into one .lloyd file
    # so you can move him from phone → server → laptop later.
    # ------------------------------------------------------------------

    def export_brain(self, path: str | Path, trainer=None) -> str:
        """
        Export the complete brain (memory + optional neural weights)
        into a single portable .lloyd zip.
        """
        path = Path(path)
        if path.suffix != ".lloyd":
            path = path.with_suffix(".lloyd")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # memory
            mem_path = tmp / "memory.json"
            self.memory.save(str(mem_path))

            # neural weights if a trainer was given
            if trainer is not None:
                brain_path = tmp / "brain.npz"
                trainer.save_brain(brain_path)

            # meta
            meta = {
                "version": "0.5",
                "goals": self.goals,
                "has_neural": trainer is not None,
            }
            (tmp / "meta.json").write_text(json.dumps(meta, indent=2))

            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in tmp.iterdir():
                    zf.write(f, f.name)

        return str(path)

    def import_brain(self, path: str | Path, trainer=None) -> str:
        """
        Import a previously exported .lloyd file.
        Restores memory and (if present) neural weights.
        """
        path = Path(path)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp)

            mem_path = tmp / "memory.json"
            if mem_path.exists():
                self.memory.load(str(mem_path))

            brain_path = tmp / "brain.npz"
            if brain_path.exists() and trainer is not None:
                trainer.load_brain(brain_path)

            meta_path = tmp / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                if "goals" in meta:
                    self.goals = meta["goals"]

        return "brain loaded successfully"
