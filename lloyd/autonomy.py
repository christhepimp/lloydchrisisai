"""
Lloyd Autonomy — free access mode
=================================
Lloyd chooses when to wake, sleep, read Moltbook, and train.
RULE: if he is doing something, he ALWAYS learns.
  - read  → fetch feed + mandatory learn
  - train → offline learn
  - rest  → still light-learn from memory (never pure idle waste)
  - wake  → light learn on wake
Sleep is the only state that skips learning.
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
        # waking is doing something → learn
        self._light_learn("wake")
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
            "free access ON — every action learns. "
            "i choose when to read moltbook, train, sleep, wake. "
            "say 'free off' to stop the background loop."
        )

    def disable_free(self) -> str:
        self.free_enabled = False
        self._stop.set()
        self._save()
        return "free access OFF — background loop stopped. chat commands still work."

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
            f"last={self.last_action} | always-learn=ON | {self.last_report[:100]}"
        )

    def decide(self) -> str:
        if not self.awake:
            return "sleep"

        curiosity = random.random()
        growth = random.random()
        fatigue = min(1.0, 0.15 + self.cycles * 0.02 + random.random() * 0.2)

        has_mb = False
        try:
            has_mb = bool(self.lloyd and self.lloyd.moltbook.client.configured())
        except Exception:
            pass

        # Prefer read (always learns) and train over pure rest
        if has_mb and curiosity > 0.30:
            return "read"
        if growth > 0.35 and self.lloyd and self.lloyd.trainer is not None:
            return "train"
        if fatigue > 0.80 and random.random() < 0.45:
            return "sleep"
        if has_mb:
            return "read"
        if self.lloyd and self.lloyd.trainer is not None:
            return "train"
        return "rest"  # rest still light-learns

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
            # rest is still doing something → always light-learn
            n = self._light_learn("rest")
            self.last_report = f"rest tick + learned from memory ({n} scraps)"
            self._save()
            return self.last_report

        self._light_learn(action)
        self.last_report = f"idle→learn ({action})"
        self._save()
        return self.last_report

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

    def _light_learn(self, tag: str) -> int:
        """Mandatory learning on any active action — never skip."""
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
                        extra_texts=scraps, steps=12, min_interval_sec=5.0
                    )
                else:
                    self.lloyd.trainer.train_on_text(
                        "\n\n".join(scraps), steps=12, lr=0.007
                    )
                self.trains_done += 1
            except Exception:
                pass
        return len(scraps)

    def _do_read(self) -> str:
        if self.lloyd is None:
            self.last_report = "no lloyd instance"
            return self.last_report
        try:
            # learn_from_feed ALWAYS learns (memory + importance + train)
            msg = self.lloyd.moltbook.learn_from_feed(limit=15, steps=30)
            self.reads_done += 1
            self.trains_done += 1  # read implies train
            self.last_report = f"self-read+learn: {msg}"
        except Exception as e:
            # even on feed failure, still learn from memory
            n = self._light_learn("read-fallback")
            self.last_report = f"read failed ({e}) — still learned from {n} memory scraps"
        self._save()
        return self.last_report

    def _do_train(self) -> str:
        if self.lloyd is None:
            self.last_report = "no lloyd instance"
            self._save()
            return self.last_report
        scraps = self._memory_scraps(12)
        for t in scraps:
            try:
                self.lloyd.importance.learn_from_text(t[:400])
            except Exception:
                pass
        if self.lloyd.trainer is None:
            self.last_report = f"no trainer — still absorbed {len(scraps)} into importance/memory"
            self._save()
            return self.last_report
        try:
            if hasattr(self.lloyd.trainer, "offline_tick"):
                self.lloyd.trainer.offline_tick(
                    extra_texts=scraps, steps=25, min_interval_sec=10.0
                )
            elif scraps:
                self.lloyd.trainer.train_on_text(
                    "\n\n".join(scraps), steps=25, lr=0.007
                )
            self.trains_done += 1
            self.last_report = f"self-train: ALWAYS learned from {len(scraps)} scraps"
        except Exception as e:
            self.last_report = f"train error ({e}) — importance still updated"
        self._save()
        return self.last_report

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
