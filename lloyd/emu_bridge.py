"""
Lloyd ↔ ARMSX2 / PS2 full-state agent bridge
============================================
Every tick the host can push the COMPLETE game loop into Lloyd's mind:

  vision (pixels / caption)
  audio
  memory reads (any address — works for every PS2 game)
  live values (score, health, position, flags — via per-game rules JSON)
  inputs / actions / reactions
  timing

Each tick is auto-fed into VectorMemory + NumPy trainer (same path as
chat, Moltbook, crypto APIs). Generic: no hard-coded game. Rules files
map labels → RAM addresses so any title works.

Upstream: https://github.com/ARMSX2/ARMSX2  (GPL-3.0)
Legal: user supplies own BIOS + legal dumps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import time
import re
import threading

BUTTONS = (
    "cross", "circle", "square", "triangle",
    "l1", "l2", "l3", "r1", "r2", "r3",
    "start", "select", "home",
    "dpad_up", "dpad_down", "dpad_left", "dpad_right",
)
STICKS = ("left_x", "left_y", "right_x", "right_y")

RULES_DIR = Path("emu_rules")


def _parse_addr(addr: Any) -> int:
    if isinstance(addr, int):
        return addr
    s = str(addr).strip().lower()
    if s.startswith("0x"):
        return int(s, 16)
    return int(s, 0)


def _decode_value(raw: bytes, typ: str = "u32") -> Any:
    typ = (typ or "u32").lower()
    if not raw:
        return None
    try:
        if typ in ("u8", "byte"):
            return raw[0]
        if typ in ("u16", "short"):
            return int.from_bytes(raw[:2], "little", signed=False)
        if typ in ("s16",):
            return int.from_bytes(raw[:2], "little", signed=True)
        if typ in ("u32", "int", "word"):
            return int.from_bytes(raw[:4], "little", signed=False)
        if typ in ("s32",):
            return int.from_bytes(raw[:4], "little", signed=True)
        if typ in ("f32", "float"):
            import struct
            return struct.unpack("<f", raw[:4])[0]
        if typ in ("hex",):
            return raw.hex()
        if typ in ("ascii", "str"):
            return raw.split(b"\x00")[0].decode("ascii", errors="ignore")
        return raw.hex()
    except Exception:
        return raw.hex()


class EmuSession:
    def __init__(self, session_id: str = "default", game: str = ""):
        self.session_id = session_id
        self.game = game or "unknown"
        self.started_at = time.time()
        self.steps: List[Dict[str, Any]] = []
        self.last_frame_b64: str = ""
        self.last_frame_meta: Dict[str, Any] = {}
        self.last_audio: Dict[str, Any] = {}
        self.last_action: Dict[str, Any] = {}
        self.last_values: Dict[str, Any] = {}
        self.last_mem: Dict[str, Any] = {}
        self.last_tick: Dict[str, Any] = {}
        self.last_reaction: Dict[str, Any] = {}
        self.rules: Dict[str, Any] = {}
        self.frame_count = 0
        self.tick_count = 0
        self.action_count = 0
        self.reaction_count = 0
        self.learn_count = 0
        self.pending_inputs: List[Dict[str, Any]] = []
        self.auto_feed = True
        self._lock = threading.Lock()

    def load_rules(self, rules: Optional[Dict[str, Any]] = None, path: str = "") -> Dict[str, Any]:
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
                self.rules = {k: v for k, v in rules.items() if isinstance(v, dict)}
        return {"ok": True, "labels": list(self.rules.keys()), "game": self.game}

    def push_frame(self, image_b64: str = "", width: int = 0, height: int = 0, caption: str = "", fmt: str = "jpeg") -> Dict[str, Any]:
        with self._lock:
            self.frame_count += 1
            self.last_frame_b64 = (image_b64 or "")[:8_000_000]
            self.last_frame_meta = {"width": width, "height": height, "fmt": fmt, "caption": (caption or "")[:2000], "t": time.time(), "n": self.frame_count}
            self.steps.append({"t": time.time(), "type": "vision", "caption": self.last_frame_meta["caption"], "w": width, "h": height})
            self._trim_steps()
            return {"ok": True, "frames": self.frame_count, "session": self.session_id}

    def push_audio(self, transcript: str = "", level: float = 0.0, note: str = "", pcm_b64: str = "") -> Dict[str, Any]:
        with self._lock:
            self.last_audio = {"transcript": (transcript or "")[:4000], "level": float(level), "note": (note or "")[:500], "has_pcm": bool(pcm_b64), "t": time.time()}
            self.steps.append({"t": time.time(), "type": "audio", "transcript": self.last_audio["transcript"][:500], "level": float(level)})
            self._trim_steps()
            return {"ok": True, "session": self.session_id}

    def push_mem(self, reads: Optional[List[Dict[str, Any]]] = None, blob_b64: str = "", base_addr: str = "") -> Dict[str, Any]:
        import base64 as b64mod
        decoded: Dict[str, Any] = {}
        raw_store: Dict[str, str] = {}
        for item in reads or []:
            label = str(item.get("label") or item.get("addr") or "mem")
            typ = item.get("type") or "u32"
            if item.get("value") is not None:
                decoded[label] = item["value"]
                continue
            data_b64 = item.get("data_b64") or item.get("data") or ""
            if data_b64:
                try:
                    raw = b64mod.b64decode(data_b64)
                    decoded[label] = _decode_value(raw, typ)
                    raw_store[label] = raw.hex()[:64]
                except Exception:
                    decoded[label] = None
        if blob_b64 and self.rules:
            try:
                blob = b64mod.b64decode(blob_b64)
                base = _parse_addr(base_addr) if base_addr else 0
                for label, spec in self.rules.items():
                    try:
                        addr = _parse_addr(spec.get("addr", 0))
                        size = int(spec.get("size") or 4)
                        typ = spec.get("type") or "u32"
                        off = addr - base
                        if 0 <= off < len(blob):
                            decoded[label] = _decode_value(blob[off:off + size], typ)
                    except Exception:
                        pass
            except Exception:
                pass
        with self._lock:
            self.last_mem = {"t": time.time(), "raw": raw_store, "n": len(decoded)}
            self.last_values.update(decoded)
            self.steps.append({"t": time.time(), "type": "mem", "values": dict(list(decoded.items())[:40])})
            self._trim_steps()
            return {"ok": True, "values": decoded, "session": self.session_id}

    def push_values(self, values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        values = values or {}
        clean = {}
        for k, v in list(values.items())[:80]:
            key = str(k)[:64]
            if isinstance(v, (int, float, bool, str)):
                clean[key] = v if not isinstance(v, str) else v[:200]
            else:
                clean[key] = str(v)[:120]
        with self._lock:
            self.last_values.update(clean)
            self.steps.append({"t": time.time(), "type": "values", "values": clean})
            self._trim_steps()
            return {"ok": True, "values": clean, "session": self.session_id}

    def queue_action(self, buttons: Optional[List[str]] = None, sticks: Optional[Dict[str, float]] = None, hold_ms: int = 50, text: str = "") -> Dict[str, Any]:
        buttons = [b.lower().strip() for b in (buttons or []) if b]
        bad = [b for b in buttons if b not in BUTTONS]
        buttons = [b for b in buttons if b in BUTTONS]
        sticks = sticks or {}
        clean_sticks = {}
        for k in STICKS:
            if k in sticks:
                try:
                    clean_sticks[k] = max(-1.0, min(1.0, float(sticks[k])))
                except (TypeError, ValueError):
                    pass
        action = {"t": time.time(), "buttons": buttons, "sticks": clean_sticks, "hold_ms": max(0, min(int(hold_ms), 5000)), "text": (text or "")[:120], "rejected": bad}
        with self._lock:
            self.action_count += 1
            self.last_action = action
            self.pending_inputs.append(action)
            if len(self.pending_inputs) > 64:
                self.pending_inputs = self.pending_inputs[-32:]
            self.steps.append({"t": action["t"], "type": "action", "buttons": buttons, "sticks": clean_sticks, "hold_ms": action["hold_ms"]})
            self._trim_steps()
            return {"ok": True, "queued": True, "action": action, "pending": len(self.pending_inputs), "session": self.session_id}

    def push_reaction(self, reaction: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        reaction = reaction or {}
        clean = {}
        for k, v in list(reaction.items())[:40]:
            key = str(k)[:64]
            if isinstance(v, (int, float, bool, str)):
                clean[key] = v if not isinstance(v, str) else v[:200]
            else:
                clean[key] = str(v)[:120]
        with self._lock:
            self.reaction_count += 1
            self.last_reaction = clean
            self.steps.append({"t": time.time(), "type": "reaction", "reaction": clean, "values": dict(self.last_values), "action": dict(self.last_action) if self.last_action else {}})
            self._trim_steps()
            return {"ok": True, "reaction": clean, "session": self.session_id}

    def ingest_tick(self, frame=None, audio=None, values=None, mem=None, action=None, reaction=None, t_game: float = 0.0, note: str = "") -> Dict[str, Any]:
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
            self._trim_steps()
        return {"ok": True, "tick": self.tick_count, "session": self.session_id, "values": tick["values"], "action": tick["action"], "reaction": tick["reaction"], "mind_line": self._tick_to_mind_line(tick)}

    def _tick_to_mind_line(self, tick: Dict[str, Any]) -> str:
        vals = tick.get("values") or {}
        val_s = ", ".join(f"{k}={v}" for k, v in list(vals.items())[:20])
        act = tick.get("action") or {}
        btns = ",".join(act.get("buttons") or []) or "-"
        reac = tick.get("reaction") or {}
        return (
            f"ps2 tick#{tick.get('n')} [{tick.get('game')}] "
            f"see={(tick.get('caption') or '')[:100]} | hear={(tick.get('audio') or '')[:60]} | "
            f"vals={val_s or '-'} | act={btns} | reaction={json.dumps(reac)[:120]}"
        )

    def pop_inputs(self, max_n: int = 16) -> List[Dict[str, Any]]:
        with self._lock:
            out = self.pending_inputs[:max_n]
            self.pending_inputs = self.pending_inputs[max_n:]
            return out

    def training_blob(self, max_chars: int = 24000) -> str:
        parts = [
            f"# PS2 full-state session {self.session_id}",
            f"# game={self.game} frames={self.frame_count} ticks={self.tick_count} actions={self.action_count} reactions={self.reaction_count}",
            f"# last_values={json.dumps(self.last_values)[:500]}",
            "",
        ]
        for i, step in enumerate(self.steps[-120:], 1):
            kind = step.get("type", "?")
            if kind == "vision":
                cap = step.get("caption") or (str(step.get("w", "")) + "x" + str(step.get("h", "")))
                parts.append(f"[see {i}] {cap}")
            elif kind == "audio":
                parts.append(f"[hear {i}] lvl={step.get('level', 0):.2f} {step.get('transcript', '')}")
            elif kind == "action":
                btns = ",".join(step.get("buttons") or []) or "-"
                parts.append(f"[act {i}] buttons={btns} sticks={step.get('sticks') or {}}")
            elif kind == "reaction":
                parts.append(f"[reaction {i}] {json.dumps(step.get('reaction') or {})[:200]} vals={json.dumps(step.get('values') or {})[:120]}")
            elif kind in ("values", "mem", "tick"):
                parts.append(f"[{kind} {i}] vals={json.dumps(step.get('values') or {})[:140]} act={json.dumps(step.get('action') or {})[:80]} reac={json.dumps(step.get('reaction') or {})[:80]}")
            else:
                parts.append(f"[{kind} {i}] {json.dumps(step)[:200]}")
        return "\n".join(parts)[:max_chars]

    def full_state(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id, "game": self.game,
            "frames": self.frame_count, "ticks": self.tick_count,
            "actions": self.action_count, "reactions": self.reaction_count,
            "learns": self.learn_count, "steps": len(self.steps),
            "pending_inputs": len(self.pending_inputs),
            "values": dict(self.last_values), "rules_labels": list(self.rules.keys()),
            "last_tick": {k: v for k, v in (self.last_tick or {}).items() if k != "image"},
            "last_frame_meta": dict(self.last_frame_meta),
            "last_audio": {k: v for k, v in self.last_audio.items() if k != "pcm"},
            "last_action": self.last_action, "last_reaction": self.last_reaction,
            "auto_feed": self.auto_feed, "uptime_s": round(time.time() - self.started_at, 1),
        }

    def summary(self) -> Dict[str, Any]:
        return self.full_state()

    def _trim_steps(self) -> None:
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
        self.train_every_n_ticks = 30

    def get_session(self, session_id: str = "default", game: str = "") -> EmuSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = EmuSession(session_id=session_id, game=game)
        elif game:
            self.sessions[session_id].game = game
        return self.sessions[session_id]

    def _feed_mind(self, line: str, train: bool = False) -> None:
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

    def observe_vision(self, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        sess = self.get_session(session_id, game=kwargs.pop("game", ""))
        out = sess.push_frame(**kwargs)
        caption = kwargs.get("caption") or ""
        if caption:
            self._feed_mind(f"ps2 vision [{sess.game}]: {caption[:400]}")
        return out

    def observe_audio(self, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        out = sess.push_audio(**kwargs)
        tr = kwargs.get("transcript") or kwargs.get("note") or ""
        if tr:
            self._feed_mind(f"ps2 audio [{sess.game}]: {tr[:300]}")
        return out

    def observe_mem(self, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        out = sess.push_mem(**kwargs)
        if out.get("values"):
            self._feed_mind(f"ps2 mem [{sess.game}]: " + ", ".join(f"{k}={v}" for k, v in list(out["values"].items())[:25]))
        return out

    def observe_values(self, session_id: str = "default", values: Optional[Dict] = None, game: str = "") -> Dict[str, Any]:
        sess = self.get_session(session_id, game=game)
        out = sess.push_values(values)
        if out.get("values"):
            self._feed_mind(f"ps2 values [{sess.game}]: " + ", ".join(f"{k}={v}" for k, v in list(out["values"].items())[:25]))
        return out

    def observe_reaction(self, session_id: str = "default", reaction: Optional[Dict] = None, game: str = "") -> Dict[str, Any]:
        sess = self.get_session(session_id, game=game)
        out = sess.push_reaction(reaction)
        if out.get("reaction"):
            self._feed_mind(
                f"ps2 reaction [{sess.game}]: {json.dumps(out['reaction'])[:300]} "
                f"after act={json.dumps(sess.last_action)[:100]} vals={json.dumps(sess.last_values)[:150]}"
            )
        return out

    def tick(self, session_id: str = "default", game: str = "", **kwargs) -> Dict[str, Any]:
        sess = self.get_session(session_id, game=game)
        out = sess.ingest_tick(**kwargs)
        line = out.get("mind_line") or ""
        do_train = self.feed_every_tick and self.train_every_n_ticks > 0 and sess.tick_count % self.train_every_n_ticks == 0
        if self.feed_every_tick and line:
            self._feed_mind(line, train=do_train)
            self.total_ticks_fed += 1
            out["fed_to_mind"] = True
            out["trained"] = bool(do_train)
        return out

    def load_rules(self, session_id: str = "default", rules: Optional[Dict] = None, path: str = "", game: str = "") -> Dict[str, Any]:
        return self.get_session(session_id, game=game).load_rules(rules=rules, path=path)

    def act(self, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        out = sess.queue_action(**kwargs)
        act = out.get("action") or {}
        self._feed_mind(f"ps2 action [{sess.game}]: buttons={act.get('buttons')} sticks={act.get('sticks')} vals={json.dumps(sess.last_values)[:200]}")
        return out

    def drain_inputs(self, session_id: str = "default", max_n: int = 16) -> Dict[str, Any]:
        return {"inputs": self.get_session(session_id).pop_inputs(max_n=max_n), "session": session_id}

    def decide(self, session_id: str = "default", goal: str = "") -> Dict[str, Any]:
        sess = self.get_session(session_id)
        cap = (sess.last_frame_meta or {}).get("caption") or "(no caption)"
        audio = (sess.last_audio or {}).get("transcript") or ""
        vals = json.dumps(sess.last_values)[:600] if sess.last_values else "{}"
        reac = json.dumps(sess.last_reaction)[:200] if sess.last_reaction else "{}"
        prompt = (
            f"You are Lloyd playing PS2 game '{sess.game}'.\nGoal: {goal or 'progress'}\n"
            f"SEE: {cap[:400]}\nHEAR: {audio[:150] or 'n/a'}\n"
            f"VALUES: {vals}\nLAST REACTION: {reac}\nLAST ACTION: {json.dumps(sess.last_action)[:120]}\n"
            'Reply ONE JSON only: {"buttons":["cross"],"sticks":{"left_x":0,"left_y":0},"hold_ms":80,"reason":"short"}\n'
            f"Buttons: {', '.join(BUTTONS)}. sticks -1..1."
        )
        if self.lloyd is None:
            action = {"buttons": ["cross"], "sticks": {}, "hold_ms": 80, "reason": "fallback"}
            self.act(session_id, buttons=["cross"], hold_ms=80)
            return {"action": action, "source": "fallback"}
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
    def _parse_action_json(text: str) -> Dict[str, Any]:
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

    def play_step(self, session_id: str = "default", goal: str = "") -> Dict[str, Any]:
        return {"session": self.get_session(session_id).full_state(), "decision": self.decide(session_id, goal=goal)}

    def learn(self, session_id: str = "default", steps: int = 24) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        blob = sess.training_blob()
        if len(blob) < 40:
            return {"message": "empty — POST /emu/tick with actions+reactions first"}
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
        return {"message": " | ".join(reports) or "learned", "steps": len(sess.steps), "ticks": sess.tick_count, "actions": sess.action_count, "reactions": sess.reaction_count, "chars": len(blob), "total_learns": self.total_learns, "ticks_fed": self.total_ticks_fed}

    def status(self) -> Dict[str, Any]:
        return {
            "emulator": "ARMSX2 full-state agent bridge (actions+reactions every tick)",
            "upstream": "https://github.com/ARMSX2/ARMSX2",
            "feed_every_tick": self.feed_every_tick,
            "train_every_n_ticks": self.train_every_n_ticks,
            "total_ticks_fed": self.total_ticks_fed,
            "total_learns": self.total_learns,
            "buttons": list(BUTTONS),
            "sessions": {sid: s.full_state() for sid, s in self.sessions.items()},
            "api": {
                "POST /emu/tick": "full loop each frame: vision+audio+values+action+reaction → brain",
                "POST /emu/action": "controller action → mind",
                "POST /emu/reaction": "game reaction/outcome → mind",
                "POST /emu/values": "live values any game",
                "POST /emu/memread": "generic RAM",
                "POST /emu/rules": "per-game label map",
                "POST /emu/play": "decide from full state",
                "POST /emu/learn": "train on trajectory",
                "GET /emu/state": "full dump",
                "GET /emu/inputs": "drain pad queue",
            },
        }
