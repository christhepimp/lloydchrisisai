"""
Lloyd - Autonomous Agent Core (no chatbot layer)
================================================
Talk = agent router + tools only.
No english_engine simple_reply chatbot — that path was slow filler.
"""

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
from lloyd.keys import status as keys_status
from lloyd.moltbook_loop import MoltbookLoop
from lloyd.autonomy import get_autonomy
from typing import Any, Dict, Union
from pathlib import Path
import zipfile
import json
import tempfile
import re
import time


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
        self.moltbook = MoltbookLoop(self)
        self.autonomy = get_autonomy(self)
        self.last_amp_report = ""
        self._think_count = 0
        self._last_offline_try = 0.0
        self.goals = [
            "improve neural weights from actions",
            "read moltbook and train when free",
            "wake and sleep on my own schedule",
            "agent tools: remember, recall, draw, moltbook, train",
        ]
        self.system_prompt = get_system_prompt()
        print("Lloyd is online. Agent mode only — no chatbot layer.")
        print("Pipeline: agent router | moltbook | free autonomy | amplifier → multi-head")

    def set_trainer(self, trainer):
        self.trainer = trainer

    def _amp(self, text: str) -> str:
        report = self.importance.attend(text)
        if not isinstance(report, str):
            report = str(report)
        self.last_amp_report = report
        return report

    def _learn(self, user_input: str, reply_text: str):
        if not reply_text:
            return
        try:
            self.importance.learn_from_text(user_input)
            self.importance.learn_from_text(reply_text)
        except Exception:
            pass
        if self.trainer is None:
            return
        try:
            self.trainer.learn_from_interaction(user_input, reply_text, steps=8, lr=0.01)
        except Exception:
            pass

    def _offline_learn(self):
        if self.trainer is None:
            return
        now = time.time()
        if now - self._last_offline_try < 40:
            return
        self._last_offline_try = now
        extra = []
        try:
            hits = self.memory.search("conversation fact lloyd user moltbook", top_k=12)
            for h in hits:
                extra.append(_hit_text(h)[:400])
        except Exception:
            pass
        try:
            self.trainer.offline_tick(extra_texts=extra, steps=20, min_interval_sec=45.0)
        except Exception:
            pass

    def _agent_talk(self, user_input: str) -> str:
        """
        Agent talk only — no chatbot phrase engine.
        Order: neural agent reply → memory hit → short agent ack.
        """
        # 1) pure-numpy model as agent voice (if trained enough)
        if self.trainer is not None:
            try:
                neural = self.trainer.generate_reply(user_input, max_new=48)
                if neural and len(neural) > 6:
                    letters = sum(ch.isalpha() for ch in neural)
                    if letters / max(len(neural), 1) > 0.55:
                        return neural.strip()[:240]
            except Exception:
                pass

        # 2) memory as agent knowledge
        try:
            hits = self.memory.search(user_input, top_k=3)
            if hits:
                bits = [_hit_text(h)[:100] for h in hits]
                return "agent recall: " + " | ".join(bits)
        except Exception:
            pass

        # 3) minimal agent ack (not a chatbot script)
        return (
            "agent online — give a task: "
            "moltbook learn | free on | remember … | recall … | draw … | status"
        )

    def _try_special(self, user_input: str) -> str | None:
        text = user_input.strip()
        lower = text.lower()

        if lower in ("free on", "free access", "autonomy on", "go free", "start free"):
            return self.autonomy.enable_free()
        if lower in ("free off", "autonomy off", "stop free"):
            return self.autonomy.disable_free()
        if lower in ("wake", "wake up", "wake yourself"):
            return self.autonomy.wake(reason="agent")
        if lower in ("sleep", "go to sleep", "sleep now"):
            return self.autonomy.sleep(reason="agent")
        if lower.startswith("sleep "):
            m = re.match(r"sleep\s+(\d+)", lower)
            if m:
                return self.autonomy.sleep(seconds=float(m.group(1)), reason="agent")
        if lower in (
            "autonomy status",
            "free status",
            "are you awake",
            "are you sleeping",
        ):
            return self.autonomy.status()
        if lower in ("do a tick", "autonomy tick", "free tick"):
            return self.autonomy.act()

        if lower in ("api keys", "api status", "keys status", "show keys"):
            return keys_status()

        if lower.startswith("moltbook") or lower.startswith("molt "):
            return self._moltbook_cmd(text)

        if lower in ("start training", "start train", "begin training", "train loop"):
            return self.training.start()

        if lower in ("training status", "train status"):
            bits = [self.training.status()]
            if self.trainer is not None:
                bits.append(self.trainer.status())
            bits.append(keys_status())
            bits.append(self.autonomy.status())
            return " | ".join(bits)

        if self.training.waiting_for_answer:
            return self.training.submit_answer(text)

        if "reward" in lower and any(w in lower for w in ("show", "status", "how many")):
            return self.rewards.status()
        if "reflection" in lower or ("reflect" in lower and "status" in lower):
            return self.reflector.status()

        if any(
            p in lower
            for p in (
                "show attention",
                "attention status",
                "attention map",
                "show amplifier",
                "amplifier status",
            )
        ):
            target = text
            for p in (
                "show attention",
                "attention status",
                "attention map",
                "show amplifier",
                "amplifier status",
            ):
                if p in lower:
                    target = re.sub(re.escape(p), "", text, flags=re.I).strip(" :-")
                    break
            if not target:
                target = "write code first then debug the code because the pattern repeats"
            return "amplifier → multi-head\n\n" + self._amp(target)

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
            return f"unknown equals for {thing}"

        m = re.match(r"^\s*does\s+(.+?)\s+equal\s+(.+?)\s*\??\s*$", lower)
        if m:
            a, b = m.group(1).strip(), m.group(2).strip()
            return f"{a} equals {b}? {equals(a, b)}"

        if "∆" in text or "Δ" in text:
            normalized = text.replace("Δ", "∆")
            self.importance.learn_from_text(normalized)
            items = parse_importance(normalized)
            if items:
                summary = ", ".join(
                    f"{w}{s:+d}{' $' if d else ''}" for w, s, d in items[:8]
                )
                return f"locked importance: {summary}"

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

    def _moltbook_cmd(self, text: str) -> str:
        rest = re.sub(r"^(moltbook|molt)\s+", "", text.strip(), flags=re.I).strip()
        low = rest.lower()

        if not rest or low in ("help", "?"):
            return (
                "moltbook agent cmds:\n"
                "• free on / free off\n"
                "• wake / sleep / autonomy status\n"
                "• moltbook learn | status\n"
                "• moltbook read only | allow post\n"
                "• moltbook post Title | body"
            )

        if low in ("read only", "readonly", "mute", "no post", "read-only"):
            return self.moltbook.set_read_only(True)

        if low in ("allow post", "allow posts", "write", "unmute", "enable post"):
            return self.moltbook.set_read_only(False)

        if low.startswith("register"):
            parts = rest.split(None, 2)
            if len(parts) < 3:
                return "usage: moltbook register AgentName description"
            return self.moltbook.register(parts[1], parts[2])

        if low in ("status", "account", "me", "home"):
            return self.moltbook.account_status() + " | " + self.autonomy.status()

        if low.startswith("learn") or low in ("train feed", "pull feed"):
            return self.moltbook.learn_from_feed()

        if low.startswith("post"):
            body = re.sub(r"^post\s+", "", rest, flags=re.I).strip()
            if "|" in body:
                title, content = [x.strip() for x in body.split("|", 1)]
            else:
                title, content = body[:80], body
            if not content:
                return "usage: moltbook post Title | body"
            return self.moltbook.post(title, content)

        if low.startswith("comment"):
            parts = rest.split(None, 2)
            if len(parts) < 3:
                return "usage: moltbook comment <post_id> text"
            return self.moltbook.comment(parts[1], parts[2])

        return self.moltbook.learn_from_feed()

    def think(self, user_input: str) -> Union[str, Dict[str, Any]]:
        self.memory.add(f"User: {user_input}", {"role": "user"})
        self._think_count += 1
        self._amp(user_input)

        if self._think_count % 4 == 0:
            self._offline_learn()

        special = self._try_special(user_input)
        if special is not None:
            out = special if special.startswith("REGISTERED") else apply_genz_style(special)
            self.memory.add(f"Lloyd: {out[:500]}", {"role": "lloyd"})
            self._learn(user_input, out[:500])
            return out

        decision = route(user_input)
        intent = decision["intent"]
        payload = decision.get("payload", user_input)

        if intent == "image":
            result = self.image_gen.generate(payload, autonomous=False)
            self.memory.add(f"Lloyd: {result['message']}", {"role": "lloyd"})
            self._learn(user_input, result.get("message", ""))
            return result

        if intent == "remember":
            self.memory.add(f"Fact: {payload}", {"role": "fact"})
            reply = f"stored: {payload}"
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            self._learn(user_input, reply)
            return reply

        if intent == "recall":
            hits = self.memory.search(payload or user_input, top_k=4)
            if not hits:
                reply = "memory empty on that — teach me"
            else:
                bits = [_hit_text(h)[:120] for h in hits]
                reply = "recall: " + " | ".join(bits)
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            self._learn(user_input, reply)
            return reply

        if intent == "status":
            tstat = self.trainer.status() if self.trainer else "no trainer"
            mode = "WRITE" if self.moltbook.allow_post else "READ-ONLY"
            reply = (
                f"agent lloyd | {self.autonomy.status()} | moltbook={mode} | {tstat}"
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            self._learn(user_input, reply)
            return reply

        if intent == "help":
            reply = (
                "agent commands:\n"
                "• free on / off | wake | sleep | autonomy status\n"
                "• moltbook learn | status | allow post\n"
                "• remember … | recall … | draw …\n"
                "• start training | api keys"
            )
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            self._learn(user_input, reply)
            return reply

        if intent == "train_hint":
            reply = "free on — or moltbook learn for one pull"
            self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
            self._learn(user_input, reply)
            return reply

        # Default: agent talk only (no chatbot simple_reply)
        reply = self._agent_talk(user_input)
        reply = apply_genz_style(reply)
        self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})
        self._learn(user_input, reply)
        return reply

    def heartbeat(self):
        if self.autonomy.free_enabled:
            self.autonomy.act()
            return
        self._offline_learn()
        try:
            if self.moltbook.client.configured():
                self.moltbook.learn_from_feed(limit=10, steps=15)
        except Exception:
            pass

    def remember(self, text: str):
        self.memory.add(text)
        if self.trainer is not None and len(text) > 15:
            try:
                self.trainer.train_on_text(text, steps=8, lr=0.008)
            except Exception:
                pass

    def recall(self, query: str, top_k: int = 3):
        return self.memory.search(query, top_k=top_k)

    def add_word(self, word: str, pos: str):
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
                "version": "0.18",
                "goals": self.goals,
                "agent_only": True,
                "has_moltbook": True,
                "has_free_autonomy": True,
                "moltbook_read_only": not self.moltbook.allow_post,
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
                try:
                    t.load_brain(tmp / "brain.npz")
                except Exception as e:
                    return f"brain loaded partially: {e}"
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
