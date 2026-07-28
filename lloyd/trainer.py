"""
Lloyd Trainer
=============
Takes raw text from uploaded files and actually trains the TinyTransformer.
Character-level for simplicity and pure-scratch purity.
"""

import numpy as np
from pathlib import Path
from model.tiny_transformer import TinyTransformer, train_step
from typing import List, Tuple
import re


class LloydTrainer:
    def __init__(self, vocab_size: int = 128, d_model: int = 64):
        self.model = TinyTransformer(
            vocab_size=vocab_size,
            d_model=d_model,
            n_layers=2,
            n_heads=4,
            d_ff=128,
            max_seq_len=64,
        )
        self.vocab_size = vocab_size
        # Simple char-level mapping (printable ASCII + a bit more)
        self.chars = sorted(set(chr(i) for i in range(32, 127)))
        self.stoi = {ch: i % vocab_size for i, ch in enumerate(self.chars)}
        self.itos = {i: ch for ch, i in self.stoi.items()}

    def text_to_ids(self, text: str) -> List[int]:
        ids = []
        for ch in text:
            if ch in self.stoi:
                ids.append(self.stoi[ch])
            else:
                ids.append(0)  # unknown
        return ids

    def make_batches(self, text: str, seq_len: int = 32, batch_size: int = 8) -> List[Tuple[np.ndarray, np.ndarray]]:
        ids = self.text_to_ids(text)
        if len(ids) < seq_len + 1:
            return []

        batches = []
        for i in range(0, len(ids) - seq_len - 1, seq_len):
            chunk = ids[i : i + seq_len + 1]
            x = np.array([chunk[:-1]])
            y = np.array([chunk[1:]])
            batches.append((x, y))
            if len(batches) >= batch_size * 4:  # limit for speed
                break
        return batches

    def train_on_text(self, text: str, steps: int = 40, lr: float = 0.01) -> dict:
        batches = self.make_batches(text)
        if not batches:
            return {"steps": 0, "final_loss": None, "message": "text too short"}

        losses = []
        for step in range(steps):
            x, y = batches[step % len(batches)]
            loss = train_step(self.model, x, y, lr=lr)
            losses.append(loss)

        return {
            "steps": steps,
            "final_loss": float(losses[-1]),
            "start_loss": float(losses[0]),
            "message": f"trained {steps} steps | loss {losses[0]:.3f} → {losses[-1]:.3f}"
        }

    def train_on_files(self, files: List[Path], steps_per_file: int = 30) -> dict:
        total_steps = 0
        reports = []
        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            # Clean a bit
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
            "message": f"Lloyd trained on {len(files)} file(s) for {total_steps} steps total."
        }
