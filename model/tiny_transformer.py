"""
Lloyd's Pure-Scratch Tiny Transformer
=====================================
Decoder-only Transformer written from absolute zero.
No PyTorch, no TensorFlow, no Hugging Face — only NumPy.

Now with a working (simplified) training step that actually updates weights.
Full multi-head attention backprop will be refined further.

Portable: save() / load() so the brain can move between phone, server, laptop.
"""

import numpy as np
from typing import List, Optional, Dict
from pathlib import Path
import json


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(x)
    return e / (np.sum(e, axis=axis, keepdims=True) + 1e-9)


def layer_norm(x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    mean = np.mean(x, axis=-1, keepdims=True)
    var = np.var(x, axis=-1, keepdims=True)
    return (x - mean) / np.sqrt(var + eps)


class MultiHeadAttention:
    def __init__(self, d_model: int, n_heads: int):
        assert d_model % n_heads == 0
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads

        scale = 0.02
        self.W_q = np.random.randn(d_model, d_model) * scale
        self.W_k = np.random.randn(d_model, d_model) * scale
        self.W_v = np.random.randn(d_model, d_model) * scale
        self.W_o = np.random.randn(d_model, d_model) * scale

    def forward(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        batch, seq_len, _ = x.shape

        Q = x @ self.W_q
        K = x @ self.W_k
        V = x @ self.W_v

        Q = Q.reshape(batch, seq_len, self.n_heads, self.d_k).transpose(0, 2, 1, 3)
        K = K.reshape(batch, seq_len, self.n_heads, self.d_k).transpose(0, 2, 1, 3)
        V = V.reshape(batch, seq_len, self.n_heads, self.d_k).transpose(0, 2, 1, 3)

        scores = (Q @ K.transpose(0, 1, 3, 2)) / np.sqrt(self.d_k)

        if mask is not None:
            scores = np.where(mask == 0, -1e9, scores)

        attn = softmax(scores, axis=-1)
        out = attn @ V

        out = out.transpose(0, 2, 1, 3).reshape(batch, seq_len, self.d_model)
        return out @ self.W_o

    def get_weights(self) -> dict:
        return {
            "W_q": self.W_q,
            "W_k": self.W_k,
            "W_v": self.W_v,
            "W_o": self.W_o,
        }

    def set_weights(self, d: dict):
        self.W_q = d["W_q"]
        self.W_k = d["W_k"]
        self.W_v = d["W_v"]
        self.W_o = d["W_o"]


class FeedForward:
    def __init__(self, d_model: int, d_ff: int):
        scale = 0.02
        self.W1 = np.random.randn(d_model, d_ff) * scale
        self.b1 = np.zeros(d_ff)
        self.W2 = np.random.randn(d_ff, d_model) * scale
        self.b2 = np.zeros(d_model)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self._cache_x = x
        self._cache_h = np.maximum(0, x @ self.W1 + self.b1)  # ReLU
        return self._cache_h @ self.W2 + self.b2

    def get_weights(self) -> dict:
        return {"W1": self.W1, "b1": self.b1, "W2": self.W2, "b2": self.b2}

    def set_weights(self, d: dict):
        self.W1 = d["W1"]
        self.b1 = d["b1"]
        self.W2 = d["W2"]
        self.b2 = d["b2"]


class TransformerBlock:
    def __init__(self, d_model: int, n_heads: int, d_ff: int):
        self.attn = MultiHeadAttention(d_model, n_heads)
        self.ffn = FeedForward(d_model, d_ff)

    def forward(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        x = x + self.attn.forward(layer_norm(x), mask)
        x = x + self.ffn.forward(layer_norm(x))
        return x

    def get_weights(self) -> dict:
        return {"attn": self.attn.get_weights(), "ffn": self.ffn.get_weights()}

    def set_weights(self, d: dict):
        self.attn.set_weights(d["attn"])
        self.ffn.set_weights(d["ffn"])


class TinyTransformer:
    """
    Decoder-only Transformer — Lloyd's first brain.
    Now with actual weight updates on the output layer + embeddings.
    Fully portable via save() / load().
    """

    def __init__(
        self,
        vocab_size: int = 128,
        d_model: int = 64,
        n_layers: int = 2,
        n_heads: int = 4,
        d_ff: int = 128,
        max_seq_len: int = 64,
    ):
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.n_layers = n_layers
        self.n_heads = n_heads
        self.d_ff = d_ff
        self.max_seq_len = max_seq_len

        scale = 0.02
        self.token_emb = np.random.randn(vocab_size, d_model) * scale
        self.pos_emb = self._sinusoidal_positional_encoding(max_seq_len, d_model)

        self.blocks = [TransformerBlock(d_model, n_heads, d_ff) for _ in range(n_layers)]

        self.W_out = np.random.randn(d_model, vocab_size) * scale
        self.b_out = np.zeros(vocab_size)

    def _sinusoidal_positional_encoding(self, max_len: int, d_model: int) -> np.ndarray:
        pe = np.zeros((max_len, d_model))
        position = np.arange(0, max_len)[:, np.newaxis]
        div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))
        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)
        return pe

    def _causal_mask(self, seq_len: int) -> np.ndarray:
        mask = np.tril(np.ones((seq_len, seq_len)))
        return mask[np.newaxis, np.newaxis, :, :]

    def forward(self, token_ids: np.ndarray) -> np.ndarray:
        batch, seq_len = token_ids.shape
        assert seq_len <= self.max_seq_len

        self._cache_ids = token_ids
        x = self.token_emb[token_ids] + self.pos_emb[:seq_len]
        self._cache_x = x.copy()

        mask = self._causal_mask(seq_len)

        for block in self.blocks:
            x = block.forward(x, mask)

        x = layer_norm(x)
        self._cache_final = x
        logits = x @ self.W_out + self.b_out
        return logits

    def generate(self, start_ids: List[int], max_new_tokens: int = 20) -> List[int]:
        ids = list(start_ids)
        for _ in range(max_new_tokens):
            x = np.array([ids[-self.max_seq_len:]])
            logits = self.forward(x)
            probs = softmax(logits[0, -1])
            next_id = int(np.random.choice(len(probs), p=probs))
            ids.append(next_id)
        return ids

    # ------------------------------------------------------------------
    # PORTABILITY — move the brain anywhere later
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        """Return a pure-Python/numpy dict of the entire brain."""
        return {
            "config": {
                "vocab_size": self.vocab_size,
                "d_model": self.d_model,
                "n_layers": self.n_layers,
                "n_heads": self.n_heads,
                "d_ff": self.d_ff,
                "max_seq_len": self.max_seq_len,
            },
            "token_emb": self.token_emb,
            "W_out": self.W_out,
            "b_out": self.b_out,
            "blocks": [b.get_weights() for b in self.blocks],
        }

    def set_state(self, state: dict):
        """Load a previously saved brain state."""
        cfg = state["config"]
        # Rebuild if shape changed (should not happen for same version)
        if (cfg["vocab_size"] != self.vocab_size or
            cfg["d_model"] != self.d_model or
            cfg["n_layers"] != self.n_layers):
            raise ValueError("Brain config mismatch — cannot load")

        self.token_emb = state["token_emb"]
        self.W_out = state["W_out"]
        self.b_out = state["b_out"]
        for block, w in zip(self.blocks, state["blocks"]):
            block.set_weights(w)

    def save(self, path: str | Path):
        """Save full brain to a .npz file (portable across devices)."""
        path = Path(path)
        state = self.get_state()
        # numpy handles nested arrays
        np.savez_compressed(path, **{
            "config": json.dumps(state["config"]),
            "token_emb": state["token_emb"],
            "W_out": state["W_out"],
            "b_out": state["b_out"],
            **{f"block_{i}_attn_W_q": b["attn"]["W_q"] for i, b in enumerate(state["blocks"])},
            **{f"block_{i}_attn_W_k": b["attn"]["W_k"] for i, b in enumerate(state["blocks"])},
            **{f"block_{i}_attn_W_v": b["attn"]["W_v"] for i, b in enumerate(state["blocks"])},
            **{f"block_{i}_attn_W_o": b["attn"]["W_o"] for i, b in enumerate(state["blocks"])},
            **{f"block_{i}_ffn_W1": b["ffn"]["W1"] for i, b in enumerate(state["blocks"])},
            **{f"block_{i}_ffn_b1": b["ffn"]["b1"] for i, b in enumerate(state["blocks"])},
            **{f"block_{i}_ffn_W2": b["ffn"]["W2"] for i, b in enumerate(state["blocks"])},
            **{f"block_{i}_ffn_b2": b["ffn"]["b2"] for i, b in enumerate(state["blocks"])},
        })

    def load(self, path: str | Path):
        """Load full brain from a .npz file."""
        path = Path(path)
        data = np.load(path, allow_pickle=False)
        config = json.loads(str(data["config"]))

        state = {
            "config": config,
            "token_emb": data["token_emb"],
            "W_out": data["W_out"],
            "b_out": data["b_out"],
            "blocks": [],
        }
        for i in range(config["n_layers"]):
            state["blocks"].append({
                "attn": {
                    "W_q": data[f"block_{i}_attn_W_q"],
                    "W_k": data[f"block_{i}_attn_W_k"],
                    "W_v": data[f"block_{i}_attn_W_v"],
                    "W_o": data[f"block_{i}_attn_W_o"],
                },
                "ffn": {
                    "W1": data[f"block_{i}_ffn_W1"],
                    "b1": data[f"block_{i}_ffn_b1"],
                    "W2": data[f"block_{i}_ffn_W2"],
                    "b2": data[f"block_{i}_ffn_b2"],
                },
            })
        self.set_state(state)


def cross_entropy_loss_and_grad(logits: np.ndarray, targets: np.ndarray):
    batch, seq, vocab = logits.shape
    logits_flat = logits.reshape(-1, vocab)
    targets_flat = targets.reshape(-1)

    probs = softmax(logits_flat, axis=-1)
    loss = -np.mean(np.log(probs[np.arange(len(targets_flat)), targets_flat] + 1e-9))

    grad = probs.copy()
    grad[np.arange(len(targets_flat)), targets_flat] -= 1.0
    grad = grad.reshape(batch, seq, vocab) / (batch * seq)

    return float(loss), grad


def train_step(model: TinyTransformer, batch_x: np.ndarray, batch_y: np.ndarray, lr: float = 3e-3) -> float:
    logits = model.forward(batch_x)
    loss, d_logits = cross_entropy_loss_and_grad(logits, batch_y)

    d_final = d_logits @ model.W_out.T
    d_W_out = model._cache_final.transpose(0, 2, 1) @ d_logits
    d_W_out = np.sum(d_W_out, axis=0)
    d_b_out = np.sum(d_logits, axis=(0, 1))

    model.W_out -= lr * d_W_out
    model.b_out -= lr * d_b_out

    for b in range(batch_x.shape[0]):
        for t in range(batch_x.shape[1]):
            tok = batch_x[b, t]
            model.token_emb[tok] -= lr * d_final[b, t]

    return loss


if __name__ == "__main__":
    print("Lloyd's Tiny Transformer — pure scratch + learning + portable")
    model = TinyTransformer(vocab_size=64, d_model=32, n_layers=2, n_heads=4, d_ff=64, max_seq_len=32)
    batch_x = np.random.randint(0, 64, size=(8, 12))
    batch_y = np.random.randint(0, 64, size=(8, 12))
    for step in range(10):
        loss = train_step(model, batch_x, batch_y, lr=0.01)
        if step % 5 == 0:
            print(f"Step {step:02d} | loss = {loss:.4f}")
    model.save("/tmp/lloyd_test_brain.npz")
    model2 = TinyTransformer(vocab_size=64, d_model=32, n_layers=2, n_heads=4, d_ff=64, max_seq_len=32)
    model2.load("/tmp/lloyd_test_brain.npz")
    print("Save/load OK")
