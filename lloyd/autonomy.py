"""
Lloyd Autonomy — free access mode
=================================
Prefer FRESH external data (Moltbook feed) first.
Memory is fallback only when feed is empty/unavailable.
Every active action still learns. Sleep skips learning.
"""

from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path
from typing import List, Optional

_STATE_PATH = Path(__file__).resolve().parent.parent / "lloyd_autonomy.json"


class Autonomy:
    ACTIONS = ("read", "train", "rest", "sleep", "wake", "idle")

    def __init__(self, lloyd=None):
        self.lloyd = lloyd
        self.awake = True
        self.free_enabled = False
        self.min_sleep_sec = 120.0
        self.max_sleep_sec = 1800.0
        self.tick_sec = 45.0
        self.reads_done = 0
        self.trains_done = 0
        self.cycles = 0
        self.last_action = "idle"
        self.last_report = ""
        self.wake_at: float = 0.0
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            if _STATE_PATH.exists():
                d = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
                self.awake = bool(d.get("awake", True))
                self.free_enabled = bool(d.get("free_enabled", False))
                self.reads_done = int(d.get("reads_done", 0))
                self.trains_done = int(d.get("trains_done", 0))
                self.cycles = int(d.get("cycles", 0))
                self.last_action = str(d.get("last_action", "idle"))
                self.wake_at = float(d.get("wake_at", 0))
        except Exception:
            pass

    def _save(self):
        try:
            _STATE_PATH.write_text(
                json.dumps(
                    {
                        "awake": self.awake,
                        "free_enabled": self.free_enabled,
                        "reads_done": self.reads_done,
                        "trains_done": self.trains_done,
                        "cycles": self.cycles,
                        "last_action": self.last_action,
                        "wake_at": self.wake_at,
                        "last_report": self.last_report[:500],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def wake(self, reason: str = "manual") -> str:
        with self._lock:
            self.awake = True
            self.wake_at = 0.0
            self.last_action = "wake"
            self.last_report = f"woke up ({reason})"
            self._save()
        # prefer fresh feed on wake; memory only if feed fails
        self._prefer_fresh_or_memory("wake")
        return self.last_report

    def sleep(self, seconds: Optional[float] = None, reason: str = "manual") -> str:
        with self._lock:
            secs = seconds if seconds is not None else random.uniform(
                self.min_sleep_sec, min(600.0, self.max_sleep_sec)
            )
            secs = max(self.min_sleep_sec, min(self.max_sleep_sec, float(secs)))
            self.awake = False
            self.wake_at = time.time() + secs
            self.last_action = "sleep"
            self.last_report = f"sleeping {secs:.0f}s ({reason}) — will self-wake"
            self._save()
        return self.last_report

    def enable_free(self) -> str:
        self.free_enabled = True
        self.awake = True
        self._save()
        self._ensure_thread()
        return (
            "free access ON — fresh Moltbook/chat first, memory only as fallback. "
            "say 'free off' to stop the background loop."
        )

    def disable_free(self) -> str:
        self.free_enabled = False
        self._stop.set()
        self._save()
        return "free access OFF — background loop stopped."

    def status(self) -> str:
        mode = "FREE" if self.free_enabled else "manual"
        state = "AWAKE" if self.awake else "ASLEEP"
        until = ""
        if not self.awake and self.wake_at:
            left = max(0, self.wake_at - time.time())
            until = f" | wakes_in={left:.0f}s"
        return (
            f"autonomy={mode} state={state}{until} | "
            f"reads={self.reads_done} trains={self.trains_done} cycles={self.cycles} | "
            f"last={self.last_action} | prefer=fresh-external | {self.last_report[:90]}"
        )

    def _has_moltbook(self) -> bool:
        try:
            return bool(self.lloyd and self.lloyd.moltbook.client.configured())
        except Exception:
            return False

    def decide(self) -> str:
        if not self.awake:
            return "sleep"
        fatigue = min(1.0, 0.15 + self.cycles * 0.02 + random.random() * 0.2)
        # Strong preference: fresh external read when key exists
        if self._has_moltbook() and random.random() > 0.2:
            return "read"
        if fatigue > 0.85 and random.random() < 0.4:
            return "sleep"
        if self.lloyd and self.lloyd.trainer is not None:
            return "train"  # train tries feed first, then memory
        return "rest"

    def act(self, action: Optional[str] = None) -> str:
        action = action or self.decide()
        self.cycles += 1
        self.last_action = action

        if action == "wake":
            return self.wake(reason="self")
        if action == "sleep":
            return self.sleep(reason="self")

        if not self.awake:
            if self.wake_at and time.time() >= self.wake_at:
                return self.wake(reason="self-timer")
            left = max(0, self.wake_at - time.time()) if self.wake_at else 0
            self.last_report = f"still asleep ({left:.0f}s left)"
            self._save()
            return self.last_report

        if action == "read":
            return self._do_read()
        if action == "train":
            return self._do_train()
        if action == "rest":
            return self._prefer_fresh_or_memory("rest")

        return self._prefer_fresh_or_memory(action)

    def _memory_scraps(self, k: int = 10) -> List[str]:
        extra: List[str] = []
        if self.lloyd is None:
            return extra
        try:
            hits = self.lloyd.memory.search("moltbook fact conversation lloyd", top_k=k)
            for h in hits:
                if isinstance(h, tuple):
                    extra.append(str(h[0])[:400])
                elif isinstance(h, dict):
                    extra.append(str(h.get("text", h))[:400])
                else:
                    extra.append(str(h)[:400])
        except Exception:
            pass
        return extra

    def _learn_memory_fallback(self, tag: str, steps: int = 12) -> int:
        """Only when fresh external data is unavailable."""
        if self.lloyd is None:
            return 0
        scraps = self._memory_scraps(8)
        for t in scraps[:6]:
            try:
                self.lloyd.importance.learn_from_text(t[:400])
            except Exception:
                pass
        if self.lloyd.trainer is not None and scraps:
            try:
                if hasattr(self.lloyd.trainer, "offline_tick"):
                    self.lloyd.trainer.offline_tick(
                        extra_texts=scraps, steps=steps, min_interval_sec=5.0
                    )
                else:
                    self.lloyd.trainer.train_on_text(
                        "\n\n".join(scraps), steps=steps, lr=0.007
                    )
                self.trains_done += 1
            except Exception:
                pass
        return len(scraps)

    def _prefer_fresh_or_memory(self, tag: str) -> str:
        """Fresh Moltbook first; memory only if feed fails or no key."""
        if self._has_moltbook():
            try:
                msg = self.lloyd.moltbook.learn_from_feed(limit=12, steps=20)
                if "no train text" not in msg and "no MOLTBOOK" not in msg:
                    self.reads_done += 1
                    self.trains_done += 1
                    self.last_report = f"{tag}: fresh feed — {msg}"
                    self._save()
                    return self.last_report
            except Exception as e:
                n = self._learn_memory_fallback(tag)
                self.last_report = f"{tag}: feed error ({e}) — memory fallback ({n})"
                self._save()
                return self.last_report
        n = self._learn_memory_fallback(tag)
        self.last_report = f"{tag}: no feed — memory fallback ({n})"
        self._save()
        return self.last_report

    def _do_read(self) -> str:
        if self.lloyd is None:
            self.last_report = "no lloyd instance"
            return self.last_report
        try:
            msg = self.lloyd.moltbook.learn_from_feed(limit=15, steps=30)
            self.reads_done += 1
            self.trains_done += 1
            self.last_report = f"self-read FRESH: {msg}"
        except Exception as e:
            n = self._learn_memory_fallback("read-fallback")
            self.last_report = f"read failed ({e}) — memory fallback ({n})"
        self._save()
        return self.last_report

    def _do_train(self) -> str:
        """Train prefers a fresh feed pull; memory only if that fails."""
        return self._prefer_fresh_or_memory("train")

    def _ensure_thread(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="lloyd-free", daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set() and self.free_enabled:
            try:
                if not self.awake:
                    if self.wake_at and time.time() >= self.wake_at:
                        self.wake(reason="self-timer")
                    else:
                        self._stop.wait(15.0)
                        continue
                self.act()
                pause = self.tick_sec + random.uniform(-10, 40)
                if self.last_action == "sleep":
                    pause = 15.0
                self._stop.wait(max(10.0, pause))
            except Exception:
                self._stop.wait(30.0)

    def attach(self, lloyd):
        self.lloyd = lloyd
        if self.free_enabled:
            self._ensure_thread()


_autonomy: Optional[Autonomy] = None


def get_autonomy(lloyd=None) -> Autonomy:
    global _autonomy
    if _autonomy is None:
        _autonomy = Autonomy(lloyd)
    elif lloyd is not None:
        _autonomy.attach(lloyd)
    return _autonomy


def start_free(lloyd=None) -> str:
    a = get_autonomy(lloyd)
    return a.enable_free()
