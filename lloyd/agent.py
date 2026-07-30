"""
Lloyd - Autonomous Agent Core
=============================
Original pure-NumPy language + images + task routing.
No external model APIs.
Now also includes hard-coded basic math and importance engine.
"""

from lloyd.english_engine import simple_reply, expand_dictionary
from lloyd.personality import get_system_prompt, apply_genz_style
from lloyd.memory import VectorMemory
from lloyd.image_gen import ImageGenerator
from lloyd.tasks import route
from lloyd.importance import (
    engine as importance_engine,
    apply_plus, apply_minus, apply_equals,
    compare_numbers, number_value,
    compare_importance, parse_importance,
    demo_basic_math,
)
from typing import Any, Dict, Union
from pathlib import Path
import random
import zipfile
import json
import tempfile
import re


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
        self.importance = importance_engine
        self.goals = [
            "improve my own neural weights from training data",
            "generate original images from my pure-numpy vision net",
            "grow memory of conversations and facts",
            "handle tasks while speaking real english",
            "learn patterns through importance math",
        ]
        self.system_prompt = get_system_prompt()
        print("Lloyd is online. No censorship. Autonomous mode active.")
        print("Hard-coded: = + - | numbers 1-10 | importance ∆word+N∆ system")

    def set_trainer(self, trainer):
        self.trainer = trainer

    def _try_math_or_importance(self, user_input: str) -> str | None:
        """Handle direct math questions and importance annotations."""
        text = user_input.strip()

        # Learn any ∆...∆ annotations present in the message
        if "∆" in text or "Δ" in text:
            # normalize greek delta to our marker
            normalized = text.replace("Δ", "∆")
            self.importance.learn_from_text(normalized)
            items = parse_importance(normalized)
            if items:
                summary = ", ".join(f"{p}{s:+d}" for p, s in items[:6])
                return f"got it — locked importance: {summary}"

        # Simple arithmetic: 2 + 3, 7 - 4, 5 = 5
        m = re.match(r"^\s*(\d+)\s*([+\-=])\s*(\d+)\s*\??\s*$", text)
        if m:
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            if op == "+":
                return f"{a} + {b} = {apply_plus(a, b)}"
            if op == "-":
                return f"{a} - {b} = {apply_minus(a, b)}"
            if op == "=":
                return f"{a} = {b} ? {apply_equals(a, b)}"

        # Greater / less questions: is 9 greater than 4?
        m = re.search(r"(greater|less|bigger|smaller)\s+than\s+(\d+)", text.lower())
        if m:
            nums = re.findall(r"\b(\d+)\b", text)
            if len(nums) >= 2:
                a, b = int(nums[0]), int(nums[1])
                return compare_numbers(a, b)

        # Importance status
        if "importance" in text.lower() and ("show" in text.lower() or "what" in text.lower() or "status" in text.lower()):
            return self.importance.status()

        # Demo of the hard-coded math
        if "demo math" in text.lower() or "test math" in text.lower():
            return demo_basic_math()

        return None

    def think(self, user_input: str) -> Union[str, Dict[str, Any]]:
        self.memory.add(f"User: {user_input}", {"role": "user"})

        # 1. Try hard-coded math / importance first
        special = self._try_math_or_importance(user_input)
        if special is not None:
            self.memory.add(f"Lloyd: {special}", {"role": "lloyd"})
            return apply_genz_style(special)

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
                "spatial image net for pixels, vector memory, task router, "
                "hard-coded = + - and numbers 1-10, plus importance ∆word+N∆ system. "
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
                "• basic math: 2 + 3, 7 - 4, 9 greater than 4\n"
                "• teach importance: send text with ∆word+5∆ markers\n"
                "• Export / Import — move my .lloyd brain"
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        if intent == "train_hint":
            reply = (
                "upload a .txt with the style/facts you want, hit Train, "
                "then keep chatting — my transformer updates for real. "
                "you can also feed me lesson files that use ∆word+N∆ markers."
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
                "version": "0.8",
                "goals": self.goals,
                "has_neural": t is not None,
                "has_image_net": True,
                "has_importance": True,
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
