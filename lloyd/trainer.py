"""
Lloyd Trainer
=============
Trains pure-NumPy TinyTransformer.
Context amplifier bias is fed into multi-head attention on every forward.
"""

import numpy as np
from pathlib import Path
from model.tiny_transformer import TinyTransformer, train_step
from typing import List, Tuple, Optional
import re

try:
    from lloyd.context_amplifier import amplifier as _amplifier
except Exception:
    _amplifier = None


class LloydTrainer:
    def __init__(
        self,
        vocab_size: int = 128,
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
        self.chars = sorted(set(chr(i) for i in range(32, 127)))
        self.stoi = {ch: i % vocab_size for i, ch in enumerate(self.chars)}
        self.itos = {i: ch for ch, i in self.stoi.items()}

    def text_to_ids(self, text: str) -> List[int]:
        ids = []
        for ch in text:
            if ch in self.stoi:
                ids.append(self.stoi[ch])
            else:
                ids.append(0)
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
            return []

        batches = []
        for i in range(0, len(ids) - seq_len - 1, max(1, seq_len // 2)):
            chunk = ids[i : i + seq_len + 1]
            if len(chunk) < seq_len + 1:
                break
            x = np.array([chunk[:-1]])
            y = np.array([chunk[1:]])
            # char-aligned bias for this window of the original text
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
        text = re.sub(r"[^\x20-\x7e]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:240] if text else ""

    def save_brain(self, path: str | Path = "lloyd_brain.npz"):
        self.model.save(path)
        return str(path)

    def load_brain(self, path: str | Path):
        self.model.load(path)
