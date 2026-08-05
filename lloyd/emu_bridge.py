"""
Lloyd ↔ ARMSX2 / PS2 emulator bridge
====================================
Normal HTTP API under the hood so Lloyd can:
  - SEE  the game (vision frames)
  - HEAR the game (audio notes / levels)
  - ACT  (controller buttons + sticks)
  - LEARN from every step (memory + trainer)

Upstream emulator (do not vendor full source here):
  https://github.com/ARMSX2/ARMSX2  (GPL-3.0, PCSX2-based, ARM64)

Legal: user supplies own PS2 BIOS + legally obtained game dumps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import base64
import json
import time
import re
import threading

# DualShock-style button names Lloyd can press
BUTTONS = (
    "cross", "circle", "square", "triangle",
    "l1", "l2", "l3", "r1", "r2", "r3",
    "start", "select", "home",
    "dpad_up", "dpad_down", "dpad_left", "dpad_right",
)

STICKS = ("left_x", "left_y", "right_x", "right_y")  # -1.0 .. 1.0


class EmuSession:
    """One live PS2 play session Lloyd is observing / controlling."""

    def __init__(self, session_id: str = "default", game: str = ""):
        self.session_id = session_id
        self.game = game or "unknown"
        self.started_at = time.time()
        self.steps: List[Dict[str, Any]] = []
        self.last_frame_b64: str = ""
        self.last_frame_meta: Dict[str, Any] = {}
        self.last_audio: Dict[str, Any] = {}
        self.last_action: Dict[str, Any] = {}
        self.frame_count = 0
        self.action_count = 0
        self.learn_count = 0
        # Pending inputs for a local backend / host injector to consume
        self.pending_inputs: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def push_frame(
        self,
        image_b64: str = "",
        width: int = 0,
        height: int = 0,
        caption: str = "",
        fmt: str = "jpeg",
    ) -> Dict[str, Any]:
        with self._lock:
            self.frame_count += 1
            self.last_frame_b64 = (image_b64 or "")[:8_000_000]
            self.last_frame_meta = {
                "width": width,
                "height": height,
                "fmt": fmt,
                "caption": (caption or "")[:2000],
                "t": time.time(),
                "n": self.frame_count,
            }
            self.steps.append({
                "t": time.time(),
                "type": "vision",
                "caption": self.last_frame_meta["caption"],
                "w": width,
                "h": height,
            })
            if len(self.steps) > 500:
                self.steps = self.steps[-400:]
            return {"ok": True, "frames": self.frame_count, "session": self.session_id}

    def push_audio(
        self,
        transcript: str = "",
        level: float = 0.0,
        note: str = "",
        pcm_b64: str = "",
    ) -> Dict[str, Any]:
        with self._lock:
            self.last_audio = {
                "transcript": (transcript or "")[:4000],
                "level": float(level),
                "note": (note or "")[:500],
                "has_pcm": bool(pcm_b64),
                "t": time.time(),
            }
            self.steps.append({
                "t": time.time(),
                "type": "audio",
                "transcript": self.last_audio["transcript"][:500],
                "level": float(level),
            })
            return {"ok": True, "session": self.session_id}

    def queue_action(
        self,
        buttons: Optional[List[str]] = None,
        sticks: Optional[Dict[str, float]] = None,
        hold_ms: int = 50,
        text: str = "",
    ) -> Dict[str, Any]:
        """Queue controller input for the host/injector backend."""
        buttons = [b.lower().strip() for b in (buttons or []) if b]
        bad = [b for b in buttons if b not in BUTTONS]
        buttons = [b for b in buttons if b in BUTTONS]
        sticks = sticks or {}
        clean_sticks = {}
        for k in STICKS:
            if k in sticks:
                try:
                    v = float(sticks[k])
                    clean_sticks[k] = max(-1.0, min(1.0, v))
                except (TypeError, ValueError):
                    pass
        action = {
            "t": time.time(),
            "buttons": buttons,
            "sticks": clean_sticks,
            "hold_ms": max(0, min(int(hold_ms), 5000)),
            "text": (text or "")[:120],
            "rejected": bad,
        }
        with self._lock:
            self.action_count += 1
            self.last_action = action
            self.pending_inputs.append(action)
            if len(self.pending_inputs) > 64:
                self.pending_inputs = self.pending_inputs[-32:]
            self.steps.append({
                "t": action["t"],
                "type": "action",
                "buttons": buttons,
                "sticks": clean_sticks,
                "hold_ms": action["hold_ms"],
            })
            return {
                "ok": True,
                "queued": True,
                "action": action,
                "pending": len(self.pending_inputs),
                "session": self.session_id,
            }

    def pop_inputs(self, max_n: int = 16) -> List[Dict[str, Any]]:
        """Host injector drains this queue (ARMSX2 plugin / ADB / virtual pad)."""
        with self._lock:
            out = self.pending_inputs[:max_n]
            self.pending_inputs = self.pending_inputs[max_n:]
            return out

    def training_blob(self, max_chars: int = 16000) -> str:
        parts = [
            f"# PS2 / ARMSX2 session {self.session_id}",
            f"# game={self.game} frames={self.frame_count} actions={self.action_count}",
            "",
        ]
        for i, step in enumerate(self.steps[-80:], 1):
            kind = step.get("type", "?")
            if kind == "vision":
                parts.append(f"[see {i}] {step.get('caption') or f'{step.get(\"w\")}x{step.get(\"h\")}'}")
            elif kind == "audio":
                parts.append(f"[hear {i}] lvl={step.get('level', 0):.2f} {step.get('transcript', '')}")
            elif kind == "action":
                btns = ",".join(step.get("buttons") or []) or "-"
                parts.append(f"[act {i}] buttons={btns} sticks={step.get('sticks') or {}}")
            else:
                parts.append(f"[{kind} {i}] {json.dumps(step)[:200]}")
        return "\n".join(parts)[:max_chars]

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "game": self.game,
            "frames": self.frame_count,
            "actions": self.action_count,
            "learns": self.learn_count,
            "steps": len(self.steps),
            "pending_inputs": len(self.pending_inputs),
            "has_frame": bool(self.last_frame_b64),
            "last_audio": {k: v for k, v in self.last_audio.items() if k != "pcm"},
            "last_action": self.last_action,
            "uptime_s": round(time.time() - self.started_at, 1),
        }


class EmuBridge:
    """
    All-around API surface for Lloyd ↔ PS2 emulator.

    Typical agent loop (under the hood, normal HTTP):
      1. Host/plugin POSTs /emu/frame  (vision)
      2. Optional POST /emu/audio
      3. Lloyd GET /emu/state  → decide
      4. POST /emu/action     → controller
      5. POST /emu/learn      → train on trajectory
    """

    DEFAULT_PORT_HINT = 8766  # distinct from TextFiction 8765

    def __init__(self, lloyd=None, trainer=None):
        self.lloyd = lloyd
        self.trainer = trainer
        self.sessions: Dict[str, EmuSession] = {}
        self.total_learns = 0
        self.backend = "queue"  # queue | mock | adb (future)

    def get_session(self, session_id: str = "default", game: str = "") -> EmuSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = EmuSession(session_id=session_id, game=game)
        elif game:
            self.sessions[session_id].game = game
        return self.sessions[session_id]

    # ---- sensors ----
    def observe_vision(self, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        sess = self.get_session(session_id, game=kwargs.pop("game", ""))
        out = sess.push_frame(**kwargs)
        caption = kwargs.get("caption") or ""
        if self.lloyd is not None and caption:
            try:
                self.lloyd.remember(f"ps2 vision [{sess.game}]: {caption[:400]}")
            except Exception:
                pass
        return out

    def observe_audio(self, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        out = sess.push_audio(**kwargs)
        tr = kwargs.get("transcript") or kwargs.get("note") or ""
        if self.lloyd is not None and tr:
            try:
                self.lloyd.remember(f"ps2 audio [{sess.game}]: {tr[:300]}")
            except Exception:
                pass
        return out

    # ---- actuators ----
    def act(self, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        return sess.queue_action(**kwargs)

    def drain_inputs(self, session_id: str = "default", max_n: int = 16) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        return {"inputs": sess.pop_inputs(max_n=max_n), "session": session_id}

    # ---- agent decision ----
    def decide(self, session_id: str = "default", goal: str = "") -> Dict[str, Any]:
        """Ask Lloyd for one controller action from current vision/audio state."""
        sess = self.get_session(session_id)
        cap = (sess.last_frame_meta or {}).get("caption") or "(no caption)"
        audio = (sess.last_audio or {}).get("transcript") or ""
        prompt = (
            f"You are Lloyd playing PS2 game '{sess.game}'.\n"
            f"Goal: {goal or 'progress in the game'}\n"
            f"What you SEE: {cap[:600]}\n"
            f"What you HEAR: {audio[:300] or 'n/a'}\n"
            "Reply with ONE JSON object only, no markdown:\n"
            '{"buttons":["cross"],"sticks":{"left_x":0,"left_y":0},"hold_ms":80,"reason":"short"}\n'
            f"Valid buttons: {', '.join(BUTTONS)}\n"
            "sticks values -1..1. Prefer simple moves."
        )
        if self.lloyd is None:
            action = {"buttons": ["cross"], "sticks": {}, "hold_ms": 80, "reason": "fallback"}
            self.act(session_id, **{k: action[k] for k in ("buttons", "sticks", "hold_ms")})
            return {"action": action, "source": "fallback"}
        try:
            reply = self.lloyd.think(prompt)
            if isinstance(reply, dict):
                text = reply.get("message") or reply.get("reply") or str(reply)
            else:
                text = str(reply)
            action = self._parse_action_json(text)
            self.act(
                session_id,
                buttons=action.get("buttons"),
                sticks=action.get("sticks"),
                hold_ms=action.get("hold_ms", 80),
                text=action.get("reason", ""),
            )
            return {"action": action, "raw": text[:400], "source": "lloyd"}
        except Exception as e:
            action = {"buttons": ["cross"], "hold_ms": 80, "reason": "error"}
            self.act(session_id, buttons=["cross"], hold_ms=80)
            return {"action": action, "error": str(e), "source": "error"}

    @staticmethod
    def _parse_action_json(text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        # find first {...}
        m = re.search(r"\{[^{}]*\}", text, re.S)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict):
                    buttons = data.get("buttons") or []
                    if isinstance(buttons, str):
                        buttons = [buttons]
                    return {
                        "buttons": list(buttons)[:8],
                        "sticks": data.get("sticks") or {},
                        "hold_ms": int(data.get("hold_ms", 80)),
                        "reason": str(data.get("reason", ""))[:120],
                    }
            except Exception:
                pass
        # free-text button names
        found = [b for b in BUTTONS if re.search(rf"\b{re.escape(b)}\b", text, re.I)]
        return {
            "buttons": found[:4] or ["cross"],
            "sticks": {},
            "hold_ms": 80,
            "reason": text[:80],
        }

    def play_step(self, session_id: str = "default", goal: str = "") -> Dict[str, Any]:
        """One full agent tick: decide from current state + queue action."""
        decision = self.decide(session_id, goal=goal)
        sess = self.get_session(session_id)
        return {
            "session": sess.summary(),
            "decision": decision,
        }

    def learn(self, session_id: str = "default", steps: int = 24) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        blob = sess.training_blob()
        if len(blob) < 40:
            return {"message": "session too empty — push frames/actions first"}
        reports = []
        if self.lloyd is not None:
            try:
                self.lloyd.remember(blob[:1500])
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
        return {
            "message": " | ".join(reports) or "learned",
            "steps": len(sess.steps),
            "chars": len(blob),
            "total_learns": self.total_learns,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "emulator": "ARMSX2 / PCSX2-compatible bridge",
            "upstream": "https://github.com/ARMSX2/ARMSX2",
            "license_note": "GPL-3.0 upstream; BIOS+ISOs not included",
            "backend": self.backend,
            "buttons": list(BUTTONS),
            "sessions": {sid: s.summary() for sid, s in self.sessions.items()},
            "total_learns": self.total_learns,
            "api": {
                "POST /emu/frame": "vision (image_b64|caption)",
                "POST /emu/audio": "audio (transcript|level)",
                "POST /emu/action": "controller buttons+sticks",
                "GET  /emu/state": "session state for agent",
                "POST /emu/decide": "Lloyd chooses action",
                "POST /emu/play": "one agent step",
                "POST /emu/learn": "train on trajectory",
                "GET  /emu/inputs": "host drains input queue",
            },
        }
