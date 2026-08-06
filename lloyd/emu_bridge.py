"""Lloyd <-> ARMSX2 full-state bridge. Game win/loss drives reward. Train every tick."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import time
import re
import threading

from lloyd.game_outcome import derive_game_outcome

BUTTONS = (
    "cross", "circle", "square", "triangle",
    "l1", "l2", "l3", "r1", "r2", "r3",
    "start", "select", "home",
    "dpad_up", "dpad_down", "dpad_left", "dpad_right",
)
STICKS = ("left_x", "left_y", "right_x", "right_y")
RULES_DIR = Path("emu_rules")


class EmuSession:
    def __init__(self, session_id: str = "default", game: str = ""):
        self.session_id = session_id
        self.game = game or "unknown"
        self.started_at = time.time()
        self.steps: List[Dict[str, Any]] = []
        self.last_frame_b64 = ""
        self.last_frame_meta: Dict[str, Any] = {}
        self.last_audio: Dict[str, Any] = {}
        self.last_action: Dict[str, Any] = {}
        self.last_values: Dict[str, Any] = {}
        self.prev_values: Dict[str, Any] = {}
        self.last_reaction: Dict[str, Any] = {}
        self.last_outcome: Dict[str, Any] = {}
        self.rules: Dict[str, Any] = {}
        self.frame_count = 0
        self.tick_count = 0
        self.action_count = 0
        self.reaction_count = 0
        self.learn_count = 0
        self.pending_inputs: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def load_rules(self, rules=None, path: str = ""):
        if path:
            p = Path(path)
            if not p.is_file():
                p = RULES_DIR / path
            if p.is_file():
                rules = json.loads(p.read_text(encoding="utf-8"))
        if rules and isinstance(rules, dict):
            if "values" in rules and isinstance(rules["values"], dict):
                self.rules = dict(rules["values"])
                if rules.get("game"):
                    self.game = str(rules["game"])
            else:
                self.rules = {k: v for k, v in rules.items() if isinstance(v, dict) and k not in ("reward_map", "_reward")}
            if rules.get("reward_map"):
                self.rules["reward_map"] = rules["reward_map"]
        return {"ok": True, "labels": [k for k in self.rules if k != "reward_map"], "game": self.game}

    def push_frame(self, image_b64="", width=0, height=0, caption="", fmt="jpeg"):
        with self._lock:
            self.frame_count += 1
            self.last_frame_b64 = (image_b64 or "")[:8_000_000]
            self.last_frame_meta = {"width": width, "height": height, "fmt": fmt, "caption": (caption or "")[:2000], "t": time.time(), "n": self.frame_count}
            self.steps.append({"t": time.time(), "type": "vision", "caption": self.last_frame_meta["caption"], "w": width, "h": height})
            self._trim()
            return {"ok": True, "frames": self.frame_count, "session": self.session_id}

    def push_audio(self, transcript="", level=0.0, note="", pcm_b64=""):
        with self._lock:
            self.last_audio = {"transcript": (transcript or "")[:4000], "level": float(level), "note": (note or "")[:500], "t": time.time()}
            self.steps.append({"t": time.time(), "type": "audio", "transcript": self.last_audio["transcript"][:500], "level": float(level)})
            self._trim()
            return {"ok": True, "session": self.session_id}

    def push_values(self, values=None):
        values = values or {}
        clean = {}
        for k, v in list(values.items())[:80]:
            key = str(k)[:64]
            clean[key] = v if isinstance(v, (int, float, bool)) else str(v)[:200]
        with self._lock:
            self.prev_values = dict(self.last_values)
            self.last_values.update(clean)
            self.steps.append({"t": time.time(), "type": "values", "values": clean})
            self._trim()
            return {"ok": True, "values": clean, "session": self.session_id}

    def push_mem(self, reads=None, blob_b64="", base_addr=""):
        decoded = {}
        for item in reads or []:
            label = str(item.get("label") or item.get("addr") or "mem")
            if item.get("value") is not None:
                decoded[label] = item["value"]
        with self._lock:
            self.last_values.update(decoded)
            self.steps.append({"t": time.time(), "type": "mem", "values": dict(list(decoded.items())[:40])})
            self._trim()
            return {"ok": True, "values": decoded, "session": self.session_id}

    def queue_action(self, buttons=None, sticks=None, hold_ms=50, text=""):
        buttons = [b.lower().strip() for b in (buttons or []) if b]
        buttons = [b for b in buttons if b in BUTTONS]
        sticks = sticks or {}
        clean_sticks = {}
        for k in STICKS:
            if k in sticks:
                try:
                    clean_sticks[k] = max(-1.0, min(1.0, float(sticks[k])))
                except Exception:
                    pass
        action = {"t": time.time(), "buttons": buttons, "sticks": clean_sticks, "hold_ms": max(0, min(int(hold_ms), 5000)), "text": (text or "")[:120]}
        with self._lock:
            self.action_count += 1
            self.last_action = action
            self.pending_inputs.append(action)
            if len(self.pending_inputs) > 64:
                self.pending_inputs = self.pending_inputs[-32:]
            self.steps.append({"t": action["t"], "type": "action", "buttons": buttons, "sticks": clean_sticks, "hold_ms": action["hold_ms"]})
            self._trim()
            return {"ok": True, "queued": True, "action": action, "pending": len(self.pending_inputs), "session": self.session_id}

    def push_reaction(self, reaction=None):
        reaction = reaction or {}
        clean = {}
        for k, v in list(reaction.items())[:40]:
            key = str(k)[:64]
            clean[key] = v if isinstance(v, (int, float, bool)) else str(v)[:200]
        with self._lock:
            self.reaction_count += 1
            self.last_reaction = clean
            self.steps.append({"t": time.time(), "type": "reaction", "reaction": clean, "values": dict(self.last_values), "action": dict(self.last_action) if self.last_action else {}})
            self._trim()
            return {"ok": True, "reaction": clean, "session": self.session_id}

    def ingest_tick(self, frame=None, audio=None, values=None, mem=None, action=None, reaction=None, t_game=0.0, note=""):
        if frame:
            self.push_frame(image_b64=frame.get("image_b64") or frame.get("image") or "", width=int(frame.get("width") or 0), height=int(frame.get("height") or 0), caption=frame.get("caption") or frame.get("note") or "", fmt=frame.get("fmt") or "jpeg")
        if audio:
            self.push_audio(transcript=audio.get("transcript") or audio.get("text") or "", level=float(audio.get("level") or 0), note=audio.get("note") or "", pcm_b64=audio.get("pcm_b64") or "")
        if values:
            self.push_values(values)
        if mem:
            self.push_mem(reads=mem.get("reads"), blob_b64=mem.get("blob_b64") or "", base_addr=str(mem.get("base_addr") or ""))
        if action:
            self.queue_action(buttons=action.get("buttons"), sticks=action.get("sticks"), hold_ms=int(action.get("hold_ms") or 50), text=action.get("text") or action.get("reason") or "")
        if reaction:
            self.push_reaction(reaction)
        with self._lock:
            self.tick_count += 1
            tick = {
                "t": time.time(), "t_game": t_game, "n": self.tick_count, "game": self.game,
                "caption": (self.last_frame_meta or {}).get("caption", ""),
                "audio": (self.last_audio or {}).get("transcript", ""),
                "values": dict(self.last_values),
                "action": dict(self.last_action) if self.last_action else {},
                "reaction": dict(self.last_reaction) if self.last_reaction else {},
                "note": (note or "")[:300],
            }
            self.last_tick = tick
            self.steps.append({"t": tick["t"], "type": "tick", "n": self.tick_count, "values": tick["values"], "action": tick["action"], "reaction": tick["reaction"]})
            self._trim()
        vals = tick.get("values") or {}
        val_s = ", ".join(f"{k}={v}" for k, v in list(vals.items())[:16])
        act = tick.get("action") or {}
        btns = ",".join(act.get("buttons") or []) or "-"
        mind = (f"ps2 tick#{tick.get('n')} [{tick.get('game')}] see={(tick.get('caption') or '')[:80]} | "
                f"vals={val_s or '-'} | act={btns} | reaction={json.dumps(tick.get('reaction') or {})[:100]}")
        return {"ok": True, "tick": self.tick_count, "session": self.session_id, "values": tick["values"],
                "action": tick["action"], "reaction": tick["reaction"], "mind_line": mind}

    def pop_inputs(self, max_n=16):
        with self._lock:
            out = self.pending_inputs[:max_n]
            self.pending_inputs = self.pending_inputs[max_n:]
            return out

    def training_blob(self, max_chars=24000):
        parts = [f"# PS2 session {self.session_id} game={self.game} ticks={self.tick_count} actions={self.action_count} reactions={self.reaction_count}",
                 f"# last_values={json.dumps(self.last_values)[:400]}", ""]
        for i, step in enumerate(self.steps[-100:], 1):
            kind = step.get("type", "?")
            if kind == "vision":
                parts.append(f"[see {i}] {step.get('caption')}")
            elif kind == "action":
                parts.append(f"[act {i}] {step.get('buttons')} {step.get('sticks')}")
            elif kind == "reaction":
                parts.append(f"[reaction {i}] {json.dumps(step.get('reaction') or {})[:180]}")
            else:
                parts.append(f"[{kind} {i}] {json.dumps({k: step.get(k) for k in ('values', 'action', 'reaction') if k in step})[:200]}")
        return "\n".join(parts)[:max_chars]

    def full_state(self):
        return {"session_id": self.session_id, "game": self.game, "frames": self.frame_count, "ticks": self.tick_count,
                "actions": self.action_count, "reactions": self.reaction_count, "learns": self.learn_count, "steps": len(self.steps),
                "pending_inputs": len(self.pending_inputs), "values": dict(self.last_values),
                "rules_labels": [k for k in self.rules if k != "reward_map"],
                "last_action": self.last_action, "last_reaction": self.last_reaction, "last_outcome": self.last_outcome,
                "uptime_s": round(time.time() - self.started_at, 1)}

    def summary(self):
        return self.full_state()

    def _trim(self):
        if len(self.steps) > 600:
            self.steps = self.steps[-450:]


class EmuBridge:
    DEFAULT_PORT_HINT = 8766

    def __init__(self, lloyd=None, trainer=None):
        self.lloyd = lloyd
        self.trainer = trainer
        self.sessions: Dict[str, EmuSession] = {}
        self.total_learns = 0
        self.total_ticks_fed = 0
        self.backend = "queue"
        self.feed_every_tick = True
        self.train_every_n_ticks = 1  # train EVERY tick

    def get_session(self, session_id="default", game=""):
        if session_id not in self.sessions:
            self.sessions[session_id] = EmuSession(session_id=session_id, game=game)
        elif game:
            self.sessions[session_id].game = game
        return self.sessions[session_id]

    def _feed_mind(self, line: str, train: bool = False):
        if not line or self.lloyd is None:
            return
        try:
            self.lloyd.remember(line[:1500])
        except Exception:
            pass
        if train and self.trainer is not None:
            try:
                self.trainer.train_on_text(line[:2000], steps=4, lr=0.008)
            except Exception:
                pass

    def _apply_game_reward(self, sess, outcome):
        if not self.lloyd or not outcome.get("from_game"):
            return None
        oc = outcome.get("outcome") or "neutral"
        pts = int(outcome.get("reward_pts") or 0)
        try:
            if oc == "win" and pts and hasattr(self.lloyd, "rewards"):
                return self.lloyd.rewards.reward(pts, reason=f"game WIN [{sess.game}] {outcome.get('signals')}")
            if oc == "progress" and pts and hasattr(self.lloyd, "rewards"):
                return self.lloyd.rewards.reward(pts, reason=f"game progress [{sess.game}] {outcome.get('signals')}")
            if oc == "lose":
                self._feed_mind(
                    f"ps2 GAME LOSE [{sess.game}]: {outcome.get('signals')} "
                    f"act={json.dumps(sess.last_action)[:80]} vals={json.dumps(sess.last_values)[:120]}",
                    train=True,
                )
                if hasattr(self.lloyd, "rewards") and hasattr(self.lloyd.rewards, "note_game_loss"):
                    return self.lloyd.rewards.note_game_loss(f"[{sess.game}] {outcome.get('signals')}")
                return "game lose — trained, no fake reward"
        except Exception as e:
            return str(e)
        return None

    def observe_vision(self, session_id="default", **kwargs):
        sess = self.get_session(session_id, game=kwargs.pop("game", ""))
        out = sess.push_frame(**kwargs)
        if kwargs.get("caption"):
            self._feed_mind(f"ps2 vision [{sess.game}]: {kwargs['caption'][:400]}", train=True)
        return out

    def observe_audio(self, session_id="default", **kwargs):
        sess = self.get_session(session_id)
        out = sess.push_audio(**kwargs)
        tr = kwargs.get("transcript") or kwargs.get("note") or ""
        if tr:
            self._feed_mind(f"ps2 audio [{sess.game}]: {tr[:300]}", train=True)
        return out

    def observe_mem(self, session_id="default", **kwargs):
        sess = self.get_session(session_id)
        out = sess.push_mem(**kwargs)
        if out.get("values"):
            self._feed_mind(f"ps2 mem [{sess.game}]: " + ", ".join(f"{k}={v}" for k, v in list(out["values"].items())[:20]), train=True)
        return out

    def observe_values(self, session_id="default", values=None, game=""):
        sess = self.get_session(session_id, game=game)
        out = sess.push_values(values)
        if out.get("values"):
            self._feed_mind(f"ps2 values [{sess.game}]: " + ", ".join(f"{k}={v}" for k, v in list(out["values"].items())[:20]), train=True)
        return out

    def observe_reaction(self, session_id="default", reaction=None, game=""):
        sess = self.get_session(session_id, game=game)
        out = sess.push_reaction(reaction)
        outcome = derive_game_outcome(reaction=out.get("reaction"), values=sess.last_values, prev_values=sess.prev_values, rules=sess.rules)
        sess.last_outcome = outcome
        self._feed_mind(
            f"ps2 reaction [{sess.game}]: {json.dumps(out.get('reaction') or {})[:250]} "
            f"OUTCOME={outcome.get('outcome')} {outcome.get('signals')}",
            train=True,
        )
        out["outcome"] = outcome
        out["reward"] = self._apply_game_reward(sess, outcome)
        return out

    def tick(self, session_id="default", game="", **kwargs):
        sess = self.get_session(session_id, game=game)
        out = sess.ingest_tick(**kwargs)
        line = out.get("mind_line") or ""
        outcome = derive_game_outcome(
            reaction=kwargs.get("reaction") or sess.last_reaction,
            values=kwargs.get("values") or sess.last_values,
            prev_values=sess.prev_values,
            rules=sess.rules,
        )
        sess.last_outcome = outcome
        # TRAIN EVERY TICK — the game is the teacher
        if self.feed_every_tick and line:
            line2 = line + f" | OUTCOME={outcome.get('outcome')} (from game) signals={outcome.get('signals')}"
            self._feed_mind(line2, train=True)
            self.total_ticks_fed += 1
            out["fed_to_mind"] = True
            out["trained"] = True
        out["outcome"] = outcome
        out["reward"] = self._apply_game_reward(sess, outcome)
        return out

    def load_rules(self, session_id="default", rules=None, path="", game=""):
        return self.get_session(session_id, game=game).load_rules(rules=rules, path=path)

    def act(self, session_id="default", **kwargs):
        sess = self.get_session(session_id)
        out = sess.queue_action(**kwargs)
        act = out.get("action") or {}
        self._feed_mind(
            f"ps2 action [{sess.game}]: buttons={act.get('buttons')} sticks={act.get('sticks')} vals={json.dumps(sess.last_values)[:180]}",
            train=True,
        )
        return out

    def drain_inputs(self, session_id="default", max_n=16):
        return {"inputs": self.get_session(session_id).pop_inputs(max_n=max_n), "session": session_id}

    def decide(self, session_id="default", goal=""):
        sess = self.get_session(session_id)
        cap = (sess.last_frame_meta or {}).get("caption") or "(no caption)"
        vals = json.dumps(sess.last_values)[:500] if sess.last_values else "{}"
        reac = json.dumps(sess.last_reaction)[:150] if sess.last_reaction else "{}"
        oc = json.dumps(sess.last_outcome or {})[:120]
        prompt = (
            f"You are Lloyd playing PS2 '{sess.game}'. Goal: {goal or 'progress'}\n"
            f"SEE: {cap[:300]}\nVALUES: {vals}\nLAST REACTION: {reac}\nLAST OUTCOME(from game): {oc}\n"
            f"LAST ACTION: {json.dumps(sess.last_action)[:100]}\n"
            'Reply ONE JSON only: {"buttons":["cross"],"sticks":{"left_x":0,"left_y":0},"hold_ms":80,"reason":"short"}\n'
            f"Buttons: {', '.join(BUTTONS)}"
        )
        if self.lloyd is None:
            self.act(session_id, buttons=["cross"], hold_ms=80)
            return {"action": {"buttons": ["cross"], "hold_ms": 80, "reason": "fallback"}, "source": "fallback"}
        try:
            reply = self.lloyd.think(prompt)
            text = reply.get("message") or reply.get("reply") or str(reply) if isinstance(reply, dict) else str(reply)
            action = self._parse_action_json(text)
            self.act(session_id, buttons=action.get("buttons"), sticks=action.get("sticks"), hold_ms=action.get("hold_ms", 80), text=action.get("reason", ""))
            return {"action": action, "raw": text[:400], "source": "lloyd", "values_used": sess.last_values}
        except Exception as e:
            self.act(session_id, buttons=["cross"], hold_ms=80)
            return {"action": {"buttons": ["cross"], "hold_ms": 80, "reason": "error"}, "error": str(e), "source": "error"}

    @staticmethod
    def _parse_action_json(text):
        text = (text or "").strip()
        m = re.search(r"\{[^{}]*\}", text, re.S)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict):
                    buttons = data.get("buttons") or []
                    if isinstance(buttons, str):
                        buttons = [buttons]
                    return {"buttons": list(buttons)[:8], "sticks": data.get("sticks") or {}, "hold_ms": int(data.get("hold_ms", 80)), "reason": str(data.get("reason", ""))[:120]}
            except Exception:
                pass
        found = [b for b in BUTTONS if re.search(rf"\b{re.escape(b)}\b", text, re.I)]
        return {"buttons": found[:4] or ["cross"], "sticks": {}, "hold_ms": 80, "reason": text[:80]}

    def play_step(self, session_id="default", goal=""):
        return {"session": self.get_session(session_id).full_state(), "decision": self.decide(session_id, goal=goal)}

    def learn(self, session_id="default", steps=24):
        sess = self.get_session(session_id)
        blob = sess.training_blob()
        if len(blob) < 40:
            return {"message": "empty — POST /emu/tick first"}
        reports = []
        if self.lloyd is not None:
            try:
                self.lloyd.remember(blob[:2000])
                reports.append("memory updated")
            except Exception as e:
                reports.append(f"memory: {e}")
        if self.trainer is not None:
            try:
                out_dir = Path("uploads")
                out_dir.mkdir(exist_ok=True)
                fpath = out_dir / f"ps2_{session_id}_{int(time.time())}.txt"
                fpath.write_text(blob, encoding="utf-8")
                result = self.trainer.train_on_files([fpath], steps_per_file=max(8, steps))
                reports.append(result.get("message", "trained"))
                self.total_learns += 1
                sess.learn_count += 1
            except Exception as e:
                reports.append(f"train: {e}")
        return {"message": " | ".join(reports) or "learned", "ticks": sess.tick_count, "actions": sess.action_count,
                "reactions": sess.reaction_count, "total_learns": self.total_learns, "ticks_fed": self.total_ticks_fed}

    def status(self):
        return {
            "emulator": "ARMSX2 — game win/loss rules drive reward; train every tick",
            "upstream": "https://github.com/ARMSX2/ARMSX2",
            "feed_every_tick": True,
            "train_every_n_ticks": 1,
            "total_ticks_fed": self.total_ticks_fed,
            "total_learns": self.total_learns,
            "buttons": list(BUTTONS),
            "sessions": {sid: s.full_state() for sid, s in self.sessions.items()},
            "api": {
                "POST /emu/tick": "full loop -> brain + game outcome + train every tick",
                "POST /emu/reaction": "game reaction -> win/loss from game rules",
                "POST /emu/action": "controller",
                "POST /emu/values": "live values",
                "POST /emu/play": "decide",
                "POST /emu/learn": "batch train",
                "GET /emu/state": "dump",
                "GET /emu/inputs": "pad queue",
            },
        }
