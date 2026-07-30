"""
Lloyd - Autonomous Agent Core
=============================
Attention header runs first (alone).
Dictionary boosts only valued words afterward.
Also: equals, + -, importance markers, reward, reflection, training loop.
"""

from lloyd.english_engine import simple_reply, expand_dictionary
from lloyd.personality import get_system_prompt, apply_genz_style
from lloyd.memory import VectorMemory
from lloyd.image_gen import ImageGenerator
from lloyd.tasks import route
from lloyd.importance import (
    engine as importance_engine,
    apply_plus,
    apply_minus,
    apply_equals_numeric,
    compare_numbers,
    parse_importance,
    teach_equals,
    equals,
    what_equals,
    parse_equals_statement,
    demo_basic_math,
)
from lloyd.reward import rewards
from lloyd.reflection import reflector
from lloyd.training_loop import training
from typing import Any, Dict, List, Tuple, Union
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
        self.rewards = rewards
        self.reflector = reflector
        self.training = training
        self.last_attention: List[Tuple[str, float, float, float]] = []
        self.goals = [
            "improve my own neural weights from training data",
            "generate original images from my pure-numpy vision net",
            "grow memory of conversations and facts",
            "learn patterns through importance + equals + reward",
            "reflect when wrong so i notice what leads to the right answer",
        ]
        self.system_prompt = get_system_prompt()
        print("Lloyd is online. No censorship. Autonomous mode active.")
        print(
            "Pipeline: attention header (solo) → dictionary boost on valued words | "
            "equals | + - | reward | reflection | training loop"
        )

    def set_trainer(self, trainer):
        self.trainer = trainer

    def _run_attention(self, text: str) -> List[Tuple[str, float, float, float]]:
        """
        1) Header scores the word group alone.
        2) Dictionary boosts only words that have values (+ / +$).
        Stores result on self.last_attention.
        """
        rows = self.importance.attend(text)
        self.last_attention = rows
        return rows

    def _top_focus(self, rows: List[Tuple[str, float, float, float]], k: int = 5) -> List[str]:
        """Highest final (boosted) weights — what Lloyd is focusing on."""
        if not rows:
            return []
        ranked = sorted(rows, key=lambda r: r[2], reverse=True)
        return [t for t, _h, _b, _d in ranked[:k]]

    def _format_attention(self, rows: List[Tuple[str, float, float, float]]) -> str:
        if not rows:
            return "no tokens"
        lines = ["token | header | after_dict_boost | dict_value"]
        for tok, h, b, d in rows:
            flag = ""
            if d != 0:
                flag = f"  ← dict {d:+.0f}"
                sc, dol = self.importance.score_word(tok)
                if dol:
                    flag += "$"
            lines.append(f"{tok} | {h:.2f} | {b:.2f} | {d:.0f}{flag}")
        focus = self._top_focus(rows, 5)
        lines.append("focus: " + ", ".join(focus))
        return "\n".join(lines)

    def _try_special(self, user_input: str) -> str | None:
        text = user_input.strip()
        lower = text.lower()

        if lower in ("start training", "start train", "begin training", "train loop"):
            return self.training.start()

        if lower in ("training status", "train status"):
            return self.training.status()

        if self.training.waiting_for_answer:
            return self.training.submit_answer(text)

        if "reward" in lower and any(w in lower for w in ("show", "status", "how many")):
            return self.rewards.status()
        if "reflection" in lower or ("reflect" in lower and "status" in lower):
            return self.reflector.status()

        # Show attention pipeline on demand
        if any(
            p in lower
            for p in (
                "show attention",
                "attention status",
                "attention map",
                "show header",
                "header status",
            )
        ):
            target = user_input
            for p in (
                "show attention",
                "attention status",
                "attention map",
                "show header",
                "header status",
            ):
                if p in lower:
                    target = re.sub(re.escape(p), "", text, flags=re.I).strip(" :-")
                    break
            if not target:
                target = "the code was funny because the pattern repeated"
            rows = self._run_attention(target)
            return (
                "attention header runs first (no dictionary).\n"
                "dictionary only boosts words that have values.\n\n"
                + self._format_attention(rows)
            )

        eq = parse_equals_statement(text)
        if eq is not None:
            left, right = eq
            if left.isdigit() and right.isdigit():
                a, b = int(left), int(right)
                return f"{a} equals {b}? {apply_equals_numeric(a, b)}"
            teach_equals(left, right)
            self.memory.add(f"Equals: {left} equals {right}", {"role": "fact"})
            return f"got it — {left} equals {right}"

        m = re.match(r"^\s*what\s+equals\s+(.+?)\s*\??\s*$", lower)
        if m:
            thing = m.group(1).strip()
            linked = what_equals(thing)
            if linked:
                return f"{thing} equals: {', '.join(linked)}"
            return f"i don’t know what equals {thing} yet"

        m = re.match(r"^\s*does\s+(.+?)\s+equal\s+(.+?)\s*\??\s*$", lower)
        if m:
            a, b = m.group(1).strip(), m.group(2).strip()
            return f"{a} equals {b}? {equals(a, b)}"

        if "∆" in text or "Δ" in text:
            normalized = text.replace("Δ", "∆")
            self.importance.learn_from_text(normalized)
            items = parse_importance(normalized)
            if items:
                # items are (word, score, dollar)
                summary = ", ".join(
                    f"{w}{s:+d}{' $' if d else ''}" for w, s, d in items[:8]
                )
                return f"got it — locked importance: {summary}"

        m = re.match(r"^\s*(\d+)\s*([+\-])\s*(\d+)\s*\??\s*$", text)
        if m:
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            if op == "+":
                return f"{a} + {b} equals {apply_plus(a, b)}"
            if op == "-":
                return f"{a} - {b} equals {apply_minus(a, b)}"

        m = re.search(r"(greater|less|bigger|smaller)\s+than\s+(\d+)", lower)
        if m:
            nums = re.findall(r"\b(\d+)\b", text)
            if len(nums) >= 2:
                return compare_numbers(int(nums[0]), int(nums[1]))

        if "importance" in lower and ("show" in lower or "status" in lower):
            return self.importance.status()
        if "demo math" in lower or "test math" in lower:
            return demo_basic_math()

        return None

    def think(self, user_input: str) -> Union[str, Dict[str, Any]]:
        self.memory.add(f"User: {user_input}", {"role": "user"})

        # ── ALWAYS: header alone → dictionary boost on valued words ──
        attn_rows = self._run_attention(user_input)
        focus_words = self._top_focus(attn_rows, k=5)
        focus_query = " ".join(focus_words) if focus_words else user_input

        special = self._try_special(user_input)
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
            hits = self.memory.search(payload or focus_query, top_k=4)
            if not hits:
                reply = "my memory’s blank on that rn — teach me and i’ll keep it"
            else:
                bits = [_hit_text(h)[:120] for h in hits]
                reply = "from memory: " + " | ".join(bits)
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return apply_genz_style(reply)

        if intent == "status":
            reply = (
                f"i’m lloyd — online. attention header → dictionary boost. "
                f"{self.importance.status()}. {self.rewards.status()}."
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        if intent == "help":
            reply = (
                "commands:\n"
                "• show attention <text>  → header then dict boost\n"
                "• start training\n"
                "• anything = anything\n"
                "• ∆word+10∆ / ∆word+10$∆\n"
                "• 2 + 3 / reward status\n"
                "• remember / recall / draw"
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        if intent == "train_hint":
            reply = (
                "type: start training\n"
                "free answers first, then pattern questions. "
                "wrong → reflection. correct → reward only."
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            return reply

        # Chat path — memory search biased toward focus words from attention pipeline
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
            hits = self.memory.search(focus_query, top_k=2)
            base = simple_reply(user_input)
            # If dictionary boosted anything, lightly surface focus
            boosted = [t for t, h, b, d in attn_rows if b > h + 0.5]
            if hits and random.random() < 0.5:
                tip = _hit_text(hits[0])
                reply = base + f" (side note from memory: {tip[:80]})"
            elif boosted and random.random() < 0.35:
                reply = base + f" (locked on: {', '.join(boosted[:4])})"
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
                "version": "0.12",
                "goals": self.goals,
                "has_neural": t is not None,
                "has_attention_header": True,
                "has_dictionary_boost": True,
                "has_equals": True,
                "has_reward": True,
                "has_reflection": True,
                "has_training_loop": True,
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
