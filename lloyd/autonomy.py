"""
Lloyd Autonomy — free access mode
=================================
Lloyd chooses when to wake, sleep, read Moltbook, and train.
Not a fixed timer-only bot: each tick he decides based on state + simple drive.

States:
  awake  — can read feed, train, post (if unlocked), chat
  asleep — resting; background thread may still wake him on his own schedule

Run:
  python -c "from lloyd.autonomy import start_free; start_free()"
Or chat:  free on | wake | sleep | autonomy status
"""

from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_STATE_PATH = Path(__file__).resolve().parent.parent / "lloyd_autonomy.json"


class Autonomy:
    """
    Free-will scheduler for Moltbook + training.
    Lloyd picks actions; human can still force wake/sleep.
    """

    ACTIONS = ("read", "train", "rest", "sleep", "wake", "idle")

    def __init__(self, lloyd=None):
        self.lloyd = lloyd
        self.awake = True
        self.free_enabled = False  # background free loop off until started
        self.min_sleep_sec = 120.0       # shortest rest he may take
        self.max_sleep_sec = 1800.0      # longest nap (30 min)
        self.tick_sec = 45.0             # how often free loop re-decides while awake
        self.reads_done = 0
        self.trains_done = 0
        self.cycles = 0
        self.last_action = "idle"
        self.last_report = ""
        self.wake_at: float = 0.0        # if asleep, when he plans to wake
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._load()

    # ---- persistence ----
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

    # ---- human / self control ----
    def wake(self, reason: str = "manual") -> str:
        with self._lock:
            self.awake = True
            self.wake_at = 0.0
            self.last_action = "wake"
            self.last_report = f"woke up ({reason})"
            self._save()
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
            "free access ON — i choose when to read moltbook, train, sleep, and wake. "
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
            f"last={self.last_action} | {self.last_report[:120]}"
        )

    # ---- decision brain (simple drives, not a second LLM) ----
    def decide(self) -> str:
        """Pick next action while free+awake."""
        if not self.awake:
            return "sleep"

        # drives: curiosity (read), growth (train), fatigue (rest/sleep)
        curiosity = random.random()
        growth = random.random()
        fatigue = min(1.0, 0.15 + self.cycles * 0.02 + random.random() * 0.2)

        # bias toward reading if moltbook key present and few recent reads
        has_mb = False
        try:
            has_mb = bool(self.lloyd and self.lloyd.moltbook.client.configured())
        except Exception:
            pass

        if has_mb and curiosity > 0.35 and self.reads_done <= self.trains_done + 2:
            return "read"
        if growth > 0.4 and self.lloyd and self.lloyd.trainer is not None:
            return "train"
        if fatigue > 0.75 and random.random() < 0.5:
            return "sleep"
        if random.random() < 0.25:
            return "rest"
        if has_mb:
            return "read"
        return "train" if self.lloyd and self.lloyd.trainer else "rest"

    def act(self, action: Optional[str] = None) -> str:
        """Execute one autonomous action."""
        action = action or self.decide()
        self.cycles += 1
        self.last_action = action

        if action == "wake":
            return self.wake(reason="self")

        if action == "sleep":
            return self.sleep(reason="self")

        if not self.awake:
            # self-wake if nap finished
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
            self.last_report = "resting a tick (awake, not reading)"
            self._save()
            return self.last_report

        self.last_report = f"idle ({action})"
        self._save()
        return self.last_report

    def _do_read(self) -> str:
        if self.lloyd is None:
            self.last_report = "no lloyd instance"
            return self.last_report
        try:
            msg = self.lloyd.moltbook.learn_from_feed(limit=15, steps=25)
            self.reads_done += 1
            self.last_report = f"self-read: {msg}"
        except Exception as e:
            self.last_report = f"read failed: {e}"
        self._save()
        return self.last_report

    def _do_train(self) -> str:
        if self.lloyd is None or self.lloyd.trainer is None:
            self.last_report = "no trainer — skip train"
            self._save()
            return self.last_report
        try:
            # offline on memory + any recent moltbook scraps
            extra: List[str] = []
            try:
                hits = self.lloyd.memory.search("moltbook fact conversation", top_k=10)
                for h in hits:
                    if isinstance(h, tuple):
                        extra.append(str(h[0])[:400])
                    elif isinstance(h, dict):
                        extra.append(str(h.get("text", h))[:400])
                    else:
                        extra.append(str(h)[:400])
            except Exception:
                pass
            if hasattr(self.lloyd.trainer, "offline_tick"):
                self.lloyd.trainer.offline_tick(extra_texts=extra, steps=25, min_interval_sec=20.0)
            elif extra:
                blob = "\n\n".join(extra)
                self.lloyd.trainer.train_on_text(blob, steps=25, lr=0.007)
            self.trains_done += 1
            self.last_report = f"self-train: {len(extra)} memory scraps, +steps"
        except Exception as e:
            self.last_report = f"train failed: {e}"
        self._save()
        return self.last_report

    # ---- background free loop ----
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
                        # sleep in short slices so stop/wake is responsive
                        self._stop.wait(15.0)
                        continue
                report = self.act()
                # variable pace — he is not a rigid cron
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


# module-level helper used by server / CLI
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
