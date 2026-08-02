"""
Lloyd Trainer
=============
Trains pure-NumPy TinyTransformer.
Context amplifier bias is fed into multi-head attention on every forward.

Learns from:
  - every chat interaction (online)
  - continuous offline passes over memory / logs while the process is alive

vocab_size = 50 (compact char set; other chars map by ord % 50)
"""

import numpy as np
from pathlib import Path
from model.tiny_transformer import TinyTransformer, train_step
from typing import List, Tuple, Optional
import re
import time

try:
    from lloyd.context_amplifier import amplifier as _amplifier
except Exception:
    _amplifier = None

# Compact 50-char vocab: space + letters + digits + common punct
_CORE = (
    " "
    + "abcdefghijklmnopqrstuvwxyz"
    + "0123456789"
    + ".',!?-\n"
)  # 1+26+10+7 = 44
_PAD = list(":;()[]{}""/#@_+=*")
_ALL_CHARS = list(_CORE)
for ch in _PAD:
    if ch not in _ALL_CHARS:
        _ALL_CHARS.append(ch)
_ALL_CHARS = _ALL_CHARS[:50]
while len(_ALL_CHARS) < 50:
    _ALL_CHARS.append(chr(0x80 + len(_ALL_CHARS)))


class LloydTrainer:
    def __init__(
        self,
        vocab_size: int = 50,
        d_model: int = 128,
        n_layers: int = 4,
        n_heads: int = 4,
        d_ff: int = 256,
        max_seq_len: int = 96,
    ):
        self.model = TinyTransformer(
            vocab_size=vocab_size,
            d_model=d_model,
            n_layers=n_layers,
            n_heads=n_heads,
            d_ff=d_ff,
            max_seq_len=max_seq_len,
        )
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        self.chars = list(_ALL_CHARS[:vocab_size])
        self.stoi = {ch: i for i, ch in enumerate(self.chars)}
        # uppercase → lowercase slot when present
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            low = ch.lower()
            if low in self.stoi and ch not in self.stoi:
                self.stoi[ch] = self.stoi[low]
        self.itos = {i: ch for i, ch in enumerate(self.chars)}

        self.interaction_count = 0
        self.total_online_steps = 0
        self.total_offline_steps = 0
        self._last_offline = 0.0
        self._corpus_buf: List[str] = []

    def text_to_ids(self, text: str) -> List[int]:
        ids = []
        for ch in text:
            if ch in self.stoi:
                ids.append(self.stoi[ch])
            else:
                ids.append(ord(ch) % self.vocab_size)
        return ids

    def ids_to_text(self, ids: List[int]) -> str:
        return "".join(self.itos.get(i, "?") for i in ids)

    def _bias(self, text: str, seq_len: Optional[int] = None) -> Optional[np.ndarray]:
        if _amplifier is None:
            return None
        try:
            b = _amplifier.bias_for_text(text)
            if seq_len is not None:
                if b.shape[0] >= seq_len:
                    return b[:seq_len]
                return np.pad(b, (0, seq_len - b.shape[0]))
            return b
        except Exception:
            return None

    def make_batches(
        self, text: str, seq_len: int = 48, batch_size: int = 8
    ) -> List[Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]]:
        ids = self.text_to_ids(text)
        if len(ids) < seq_len + 1:
            if len(ids) < 8:
                return []
            seq_len = max(4, len(ids) - 1)

        batches = []
        step = max(1, seq_len // 2)
        for i in range(0, len(ids) - seq_len - 1, step):
            chunk = ids[i : i + seq_len + 1]
            if len(chunk) < seq_len + 1:
                break
            x = np.array([chunk[:-1]])
            y = np.array([chunk[1:]])
            window_text = text[i : i + seq_len] if i + seq_len <= len(text) else text[i:]
            bias = self._bias(window_text, seq_len=seq_len)
            batches.append((x, y, bias))
            if len(batches) >= batch_size * 8:
                break
        return batches

    def train_on_text(self, text: str, steps: int = 60, lr: float = 0.008) -> dict:
        batches = self.make_batches(text)
        if not batches:
            return {"steps": 0, "final_loss": None, "message": "text too short"}

        losses = []
        for step in range(steps):
            x, y, bias = batches[step % len(batches)]
            loss = train_step(self.model, x, y, lr=lr, importance_bias=bias)
            losses.append(loss)

        return {
            "steps": steps,
            "final_loss": float(losses[-1]),
            "start_loss": float(losses[0]),
            "message": f"trained {steps} steps | loss {losses[0]:.3f} → {losses[-1]:.3f}",
        }

    def learn_from_interaction(
        self, user_text: str, reply_text: str, steps: int = 12, lr: float = 0.01
    ) -> dict:
        """Online learning: every chat turn updates weights."""
        pair = f"User: {user_text}\nLloyd: {reply_text}\n"
        self._corpus_buf.append(pair)
        if len(self._corpus_buf) > 200:
            self._corpus_buf = self._corpus_buf[-200:]

        blob = "\n".join(self._corpus_buf[-8:])
        result = self.train_on_text(blob, steps=steps, lr=lr)
        self.interaction_count += 1
        self.total_online_steps += result.get("steps") or 0
        return result

    def offline_tick(
        self,
        extra_texts: Optional[List[str]] = None,
        steps: int = 20,
        min_interval_sec: float = 45.0,
    ) -> dict:
        """Continuous offline learning while process is alive."""
        now = time.time()
        if now - self._last_offline < min_interval_sec:
            return {"steps": 0, "message": "offline cooldown"}

        parts = list(self._corpus_buf[-40:])
        if extra_texts:
            parts.extend(t for t in extra_texts if t and len(t) > 10)
        if not parts:
            return {"steps": 0, "message": "nothing to offline-train yet"}

        blob = "\n".join(parts)
        result = self.train_on_text(blob, steps=steps, lr=0.006)
        self.total_offline_steps += result.get("steps") or 0
        self._last_offline = now
        return result

    def train_on_files(self, files: List[Path], steps_per_file: int = 50) -> dict:
        total_steps = 0
        reports = []
        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 20:
                continue
            result = self.train_on_text(text, steps=steps_per_file)
            total_steps += result["steps"]
            reports.append(f"{f.name}: {result['message']}")
            self._corpus_buf.append(text[:2000])

        return {
            "files": len(files),
            "total_steps": total_steps,
            "reports": reports,
            "message": f"Lloyd trained on {len(files)} file(s) for {total_steps} steps total.",
        }

    def generate_reply(self, prompt: str, max_new: int = 80) -> str:
        ids = self.text_to_ids(prompt)[-self.max_seq_len :]
        if not ids:
            ids = [self.stoi.get("y", 1)]
        bias = self._bias(prompt)
        out = self.model.generate(ids, max_new_tokens=max_new, importance_bias=bias)
        new_ids = out[len(ids) :]
        text = self.ids_to_text(new_ids)
        text = text.split("\n")[0].strip()
        text = re.sub(r"[^\x20-\x7e\n]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:240] if text else ""

    def status(self) -> str:
        return (
            f"trainer vocab={self.vocab_size} interactions={self.interaction_count} "
            f"online_steps={self.total_online_steps} offline_steps={self.total_offline_steps} "
            f"buffer={len(self._corpus_buf)}"
        )

    def save_brain(self, path: str | Path = "lloyd_brain.npz"):
        self.model.save(path)
        return str(path)

    def load_brain(self, path: str | Path):
        self.model.load(path)
