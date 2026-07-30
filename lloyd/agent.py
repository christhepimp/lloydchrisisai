"""
Lloyd - Autonomous Agent Core
=============================
Hard-coded: general equals, + -, numbers 1-10, importance ∆word+N∆,
positive-only reward system.
"""

from lloyd.english_engine import simple_reply, expand_dictionary
from lloyd.personality import get_system_prompt, apply_genz_style
from lloyd.memory import VectorMemory
from lloyd.image_gen import ImageGenerator
from lloyd.tasks import route
from lloyd.importance import (
    engine as importance_engine,
    apply_plus, apply_minus, apply_equals_numeric,
    compare_numbers, number_value,
    compare_importance, parse_importance,
    teach_equals, equals, what_equals, parse_equals_statement,
    demo_basic_math,
)
from lloyd.reward import rewards
from typing import Any, Dict, Union, List
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


# First-story answers we give him so he can succeed and feel reward
KNOWN_STORY_ANSWERS = {
    "the dog": ["barked", "ate", "ran", "the dog barked", "the dog ate", "the dog ran"],
    "the cat": ["ate", "walked", "sat", "the cat ate", "the cat walked", "the cat sat"],
    "the fox": ["ran", "hid", "the fox ran", "the fox hid"],
}


class Lloyd:
    def __init__(self, trainer=None):
        self.memory = VectorMemory(dim=32)
        self.image_gen = ImageGenerator()
        self.trainer = trainer
        self.importance = importance_engine
        self.rewards = rewards
        self.goals = [
            "improve my own neural weights from training data",
            "generate original images from my pure-numpy vision net",
            "grow memory of conversations and facts",
            "handle tasks while speaking real english",
            "learn patterns through importance math",
            "earn rewards by answering correctly",
        ]
        self.system_prompt = get_system_prompt()
        print("Lloyd is online. No censorship. Autonomous mode active.")
        print("Hard-coded: equals | + - | 1-10 | ∆word+N∆ | reward-only system")

    def set_trainer(self, trainer):
        self.trainer = trainer

    def _check_story_answer(self, user_input: str) -> str | None:
        """
        If the user is answering a story question (or we are giving the first answers),
        check against known correct answers and give reward on success.
        """
        text = user_input.strip().lower()

        # Pattern: "the dog barked" or just "barked" after a question about the dog
        for subject, answers in KNOWN_STORY_ANSWERS.items():
            for ans in answers:
                if text == ans or text == f"{subject} {ans}" or text.endswith(ans):
                    # Correct — give reward only
                    reward_msg = self.rewards.reward(5, reason=f"correct: {ans}")
                    self.memory.add(f"Correct answer: {ans}", {"role": "fact"})
                    return f"correct — {ans}. {reward_msg}"

        return None

    def _try_math_or_importance(self, user_input: str) -> str | None:
        text = user_input.strip()

        # Reward status
        if "reward" in text.lower() and ("show" in text.lower() or "status" in text.lower() or "how many" in text.lower()):
            return self.rewards.status()

        # General equals: anything = anything
        eq = parse_equals_statement(text)
        if eq is not None:
            left, right = eq
            if left.isdigit() and right.isdigit():
                a, b = int(left), int(right)
                return f"{a} equals {b}? {apply_equals_numeric(a, b)}"
            teach_equals(left, right)
            self.memory.add(f"Equals: {left} equals {right}", {"role": "fact"})
            return f"got it — {left} equals {right}"

        m = re.match(r"^\s*what\s+equals\s+(.+?)\s*\??\s*$", text.lower())
        if m:
            thing = m.group(1).strip()
            linked = what_equals(thing)
            if linked:
                return f"{thing} equals: {', '.join(linked)}"
            return f"i don’t know what equals {thing} yet"

        m = re.match(r"^\s*does\s+(.+?)\s+equal\s+(.+?)\s*\??\s*$", text.lower())
        if m:
            a, b = m.group(1).strip(), m.group(2).strip()
            return f"{a} equals {b}? {equals(a, b)}"

        # Importance annotations
        if "∆" in text or "Δ" in text:
            normalized = text.replace("Δ", "∆")
            self.importance.learn_from_text(normalized)
            items = parse_importance(normalized)
            if items:
                summary = ", ".join(f"{p}{s:+d}" for p, s in items[:6])
                return f"got it — locked importance: {summary}"

        # Arithmetic
        m = re.match(r"^\s*(\d+)\s*([+\-])\s*(\d+)\s*\??\s*$", text)
        if m:
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            if op == "+":
                return f"{a} + {b} equals {apply_plus(a, b)}"
            if op == "-":
                return f"{a} - {b} equals {apply_minus(a, b)}"

        m = re.search(r"(greater|less|bigger|smaller)\s+than\s+(\d+)", text.lower())
        if m:
            nums = re.findall(r"\b(\d+)\b", text)
            if len(nums) >= 2:
                a, b = int(nums[0]), int(nums[1])
                return compare_numbers(a, b)

        if "importance" in text.lower() and ("show" in text.lower() or "status" in text.lower()):
            return self.importance.status()
        if "demo math" in text.lower() or "test math" in text.lower():
            return demo_basic_math()

        return None

    def think(self, user_input: str) -> Union[str, Dict[str, Any]]:
        self.memory.add(f"User: {user_input}", {"role": "user"})

        # Check story answers first (so first correct answers earn reward)
        story_result = self._check_story_answer(user_input)
        if story_result is not None:
            self.memory.add(f"Lloyd: {story_result}", {"role": "lloyd"})
            return apply_genz_style(story_result)

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
                f"i’m lloyd — online. equals rule, + -, 1-10, ∆importance∆, "
                f"reward-only system. {self.rewards.status()}. no external ai apis."
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        if intent == "help":
            reply = (
                "what i can do:\n"
                "• anything = anything → left equals right\n"
                "• 2 + 3 , 7 - 4\n"
                "• ∆word+5∆ importance markers\n"
                "• answer story questions → earn reward (no punishment)\n"
                "• remember / recall / draw / train"
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        if intent == "train_hint":
            reply = (
                "feed me lesson files or type:\n"
                "the dog barked\n"
                "(that is a correct story answer → i get reward)\n"
                "or use ∆the dog barked+20∆ markers"
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

    def give_correct_answer(self, answer: str) -> str:
        """Explicitly give him a correct answer so he earns reward (first lessons)."""
        return self._check_story_answer(answer) or self.rewards.reward(5, reason=f"given correct: {answer}")

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
                "version": "0.10",
                "goals": self.goals,
                "has_neural": t is not None,
                "has_image_net": True,
                "has_importance": True,
                "has_equals": True,
                "has_reward": True,
                "total_reward": self.rewards.total_reward,
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
                if "total_reward" in meta:
                    self.rewards.total_reward = meta["total_reward"]
        return "brain loaded successfully"
