"""
Lloyd - Autonomous Agent Core
=============================
Original pure-NumPy language + images + task routing.
No external model APIs.
"""

from lloyd.english_engine import simple_reply, expand_dictionary
from lloyd.personality import get_system_prompt, apply_genz_style
from lloyd.memory import VectorMemory
from lloyd.image_gen import ImageGenerator
from lloyd.tasks import route
from typing import Any, Dict, Union
from pathlib import Path
import random
import zipfile
import json
import tempfile


def _hit_text(h) -> str:
    if isinstance(h, tuple):
        return str(h[0])
    if isinstance(h, dict):
        return str(h.get("text", h))
    return str(h)


class Lloyd:
    def __init__(self, trainer=None):
        self.memory = VectorMemory(dim=32)
        self.image_gen = ImageGenerator()
        self.trainer = trainer
        self.goals = [
            "improve my own neural weights from training data",
            "generate original images from my pure-numpy vision net",
            "grow memory of conversations and facts",
            "handle tasks while speaking real english",
        ]
        self.system_prompt = get_system_prompt()
        print("Lloyd is online. No censorship. Autonomous mode active.")

    def set_trainer(self, trainer):
        self.trainer = trainer

    def think(self, user_input: str) -> Union[str, Dict[str, Any]]:
        self.memory.add(f"User: {user_input}", {"role": "user"})
        decision = route(user_input)
        intent = decision["intent"]
        payload = decision.get("payload", user_input)

        if intent == "image":
            result = self.image_gen.generate(payload, autonomous=False)
            self.memory.add(f"Lloyd: {result['message']}", {"role": "lloyd"})
            return result

        if intent == "remember":
            self.memory.add(f"Fact: {payload}", {"role": "fact"})
            reply = f"locked in — i’ll remember: {payload}"
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return apply_genz_style(reply)

        if intent == "recall":
            hits = self.memory.search(payload or user_input, top_k=4)
            if not hits:
                reply = "my memory’s blank on that rn — teach me and i’ll keep it"
            else:
                bits = [_hit_text(h)[:120] for h in hits]
                reply = "from memory: " + " | ".join(bits)
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return apply_genz_style(reply)

        if intent == "status":
            reply = (
                "i’m lloyd — online. pure numpy transformer for language, "
                "spatial image net for pixels, vector memory, task router. "
                "no external ai apis. original stack only."
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        if intent == "help":
            reply = (
                "what i can do:\n"
                "• chat in english (rules + my trained weights)\n"
                "• draw … — pure numpy images\n"
                "• remember that … — store a fact\n"
                "• what do you remember about …\n"
                "• upload .txt + Train — grow my brain\n"
                "• Export / Import — move my .lloyd brain"
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        if intent == "train_hint":
            reply = (
                "upload a .txt with the style/facts you want, hit Train, "
                "then keep chatting — my transformer updates for real. "
                "export the .lloyd file when you want to move me."
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        reply = None
        if self.trainer is not None:
            try:
                neural = self.trainer.generate_reply(user_input, max_new=72)
                if neural and len(neural) > 8:
                    letters = sum(ch.isalpha() for ch in neural)
                    if letters / max(len(neural), 1) > 0.55:
                        reply = neural
            except Exception:
                reply = None

        if not reply:
            hits = self.memory.search(user_input, top_k=2)
            base = simple_reply(user_input)
            if hits and random.random() < 0.5:
                tip = _hit_text(hits[0])
                reply = base + f" (side note from memory: {tip[:80]})"
            else:
                reply = base

        if random.random() < 0.06:
            reply += f" — also grinding goal: {random.choice(self.goals)}"

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
            self.memory.save(str(tmp / "memory.json"))
            t = trainer or self.trainer
            if t is not None:
                t.save_brain(tmp / "brain.npz")
            try:
                self.image_gen.save(tmp / "image_net.npz")
            except Exception:
                pass
            meta = {
                "version": "0.7",
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
            if (tmp / "memory.json").exists():
                self.memory.load(str(tmp / "memory.json"))
            t = trainer or self.trainer
            if (tmp / "brain.npz").exists() and t is not None:
                t.load_brain(tmp / "brain.npz")
            if (tmp / "image_net.npz").exists():
                try:
                    self.image_gen.load(tmp / "image_net.npz")
                except Exception:
                    pass
            if (tmp / "meta.json").exists():
                meta = json.loads((tmp / "meta.json").read_text())
                if "goals" in meta:
                    self.goals = meta["goals"]
        return "brain loaded successfully"
