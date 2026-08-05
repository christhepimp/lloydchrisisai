"""
Lloyd ↔ Text Fiction bridge
===========================
Lets Lloyd play interactive fiction / learn from story state.
The APK (text-fiction) is a classic IF client. Lloyd receives
room text, choices, and player commands over HTTP and learns
from every turn (story patterns, dialogue, causality).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import time
import re


class TextFictionSession:
    """One play session Lloyd is learning from."""

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.turns: List[Dict[str, Any]] = []
        self.story_log: List[str] = []
        self.commands: List[str] = []
        self.started_at = time.time()
        self.last_room = ""
        self.last_choices: List[str] = []

    def observe(
        self,
        room_text: str = "",
        choices: Optional[List[str]] = None,
        command: str = "",
        meta: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        choices = choices or []
        turn = {
            "t": time.time(),
            "room": (room_text or "")[:4000],
            "choices": choices[:32],
            "command": (command or "")[:500],
            "meta": meta or {},
        }
        self.turns.append(turn)
        if room_text:
            self.story_log.append(room_text[:2000])
            self.last_room = room_text[:2000]
        if choices:
            self.last_choices = choices[:32]
        if command:
            self.commands.append(command[:500])
        return {"ok": True, "turn": len(self.turns), "session": self.session_id}

    def training_blob(self, max_chars: int = 12000) -> str:
        """Flatten session into text Lloyd can train on."""
        parts = [
            f"# Text Fiction session {self.session_id}",
            f"# turns={len(self.turns)} commands={len(self.commands)}",
            "",
        ]
        for i, turn in enumerate(self.turns[-40:], 1):
            if turn.get("room"):
                parts.append(f"[room {i}]\n{turn['room']}")
            if turn.get("choices"):
                parts.append("[choices] " + " | ".join(turn["choices"]))
            if turn.get("command"):
                parts.append(f"[player] {turn['command']}")
            parts.append("")
        blob = "\n".join(parts)
        return blob[:max_chars]

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turns": len(self.turns),
            "commands": len(self.commands),
            "last_room_preview": (self.last_room or "")[:200],
            "last_choices": self.last_choices,
            "age_sec": round(time.time() - self.started_at, 1),
        }


class TextFictionBridge:
    """Registry of sessions + learn/play helpers bound to a Lloyd instance."""

    def __init__(self, lloyd=None, trainer=None):
        self.lloyd = lloyd
        self.trainer = trainer
        self.sessions: Dict[str, TextFictionSession] = {}
        self.total_learns = 0

    def get_session(self, session_id: str = "default") -> TextFictionSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = TextFictionSession(session_id)
        return self.sessions[session_id]

    def observe(
        self,
        room_text: str = "",
        choices: Optional[List[str]] = None,
        command: str = "",
        session_id: str = "default",
        meta: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        result = sess.observe(room_text, choices, command, meta)
        if self.lloyd is not None:
            snippet = (room_text or command or "")[:300]
            if snippet:
                try:
                    self.lloyd.remember(
                        f"text-fiction[{session_id}]: {snippet}"
                    )
                except Exception:
                    pass
        return result

    def suggest_command(self, session_id: str = "default") -> Dict[str, Any]:
        """Lloyd picks a next IF command from current room + memory."""
        sess = self.get_session(session_id)
        prompt = (
            "interactive fiction turn. room:\n"
            f"{sess.last_room[:800]}\n"
            f"choices: {', '.join(sess.last_choices) if sess.last_choices else 'none'}\n"
            "reply with ONE short player command only (e.g. look, go north, talk to npc)."
        )
        if self.lloyd is None:
            cmd = (sess.last_choices[0] if sess.last_choices else "look")
            return {"command": cmd, "source": "fallback"}
        try:
            reply = self.lloyd.think(prompt)
            if isinstance(reply, dict):
                text = reply.get("message") or reply.get("reply") or ""
            else:
                text = str(reply)
            line = text.strip().split("\n")[0]
            line = re.sub(r"^(agent|lloyd|command)[:\s-]+", "", line, flags=re.I)
            line = line.strip(" .\"'")[:120] or "look"
            return {"command": line, "raw": text[:300], "source": "lloyd"}
        except Exception as e:
            return {"command": "look", "error": str(e), "source": "error"}

    def learn(self, session_id: str = "default", steps: int = 20) -> Dict[str, Any]:
        """Train Lloyd on the full session story log."""
        sess = self.get_session(session_id)
        blob = sess.training_blob()
        if len(blob) < 40:
            return {"message": "session too empty to train — play more turns first"}
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
                fpath = out_dir / f"text_fiction_{session_id}_{int(time.time())}.txt"
                fpath.write_text(blob, encoding="utf-8")
                result = self.trainer.train_on_files([fpath], steps_per_file=max(8, steps))
                reports.append(result.get("message", "trained"))
                self.total_learns += 1
            except Exception as e:
                reports.append(f"train: {e}")
        return {
            "message": " | ".join(reports) or "learned",
            "turns": len(sess.turns),
            "chars": len(blob),
            "total_learns": self.total_learns,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "sessions": {sid: s.summary() for sid, s in self.sessions.items()},
            "total_learns": self.total_learns,
        }
