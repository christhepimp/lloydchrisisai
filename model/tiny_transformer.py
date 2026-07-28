"""
Lloyd's Pure-Scratch Tiny Transformer
=====================================
Decoder-only Transformer written from absolute zero.
No PyTorch, no TensorFlow, no Hugging Face — only NumPy.

Now with a working (simplified) training step that actually updates weights.
Full multi-head attention backprop will be refined further.
"""

import numpy as np
from typing import List, Optional, Dict


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


class TransformerBlock:
    def __init__(self, d_model: int, n_heads: int, d_ff: int):
        self.attn = MultiHeadAttention(d_model, n_heads)
        self.ffn = FeedForward(d_model, d_ff)

    def forward(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        x = x + self.attn.forward(layer_norm(x), mask)
        x = x + self.ffn.forward(layer_norm(x))
        return x


class TinyTransformer:
    """
    Decoder-only Transformer — Lloyd's first brain.
    Now with actual weight updates on the output layer + embeddings.
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
            # Sample instead of pure argmax for more interesting output
            probs = softmax(logits[0, -1])
            next_id = int(np.random.choice(len(probs), p=probs))
            ids.append(next_id)
        return ids


def cross_entropy_loss_and_grad(logits: np.ndarray, targets: np.ndarray):
    """
    Returns loss and gradient w.r.t. logits.
    logits: (batch, seq, vocab)
    targets: (batch, seq)
    """
    batch, seq, vocab = logits.shape
    logits_flat = logits.reshape(-1, vocab)
    targets_flat = targets.reshape(-1)

    probs = softmax(logits_flat, axis=-1)
    loss = -np.mean(np.log(probs[np.arange(len(targets_flat)), targets_flat] + 1e-9))

    # Gradient of cross-entropy + softmax
    grad = probs.copy()
    grad[np.arange(len(targets_flat)), targets_flat] -= 1.0
    grad = grad.reshape(batch, seq, vocab) / (batch * seq)

    return float(loss), grad


def train_step(model: TinyTransformer, batch_x: np.ndarray, batch_y: np.ndarray, lr: float = 3e-3) -> float:
    """
    Working training step.
    Currently updates:
      - Output projection (W_out, b_out)
      - Token embeddings
    Full backprop through attention blocks is the next refinement.
    This already lets Lloyd start learning patterns.
    """
    logits = model.forward(batch_x)
    loss, d_logits = cross_entropy_loss_and_grad(logits, batch_y)

    # Gradient w.r.t. final hidden state
    # d_logits shape: (batch, seq, vocab)
    # W_out shape: (d_model, vocab)
    d_final = d_logits @ model.W_out.T          # (batch, seq, d_model)
    d_W_out = model._cache_final.transpose(0, 2, 1) @ d_logits  # rough
    d_W_out = np.sum(d_W_out, axis=0)           # (d_model, vocab)
    d_b_out = np.sum(d_logits, axis=(0, 1))     # (vocab,)

    # Update output layer
    model.W_out -= lr * d_W_out
    model.b_out -= lr * d_b_out

    # Simple embedding update (broadcast the final gradient back to tokens)
    # This is approximate but already produces learning signal
    for b in range(batch_x.shape[0]):
        for t in range(batch_x.shape[1]):
            tok = batch_x[b, t]
            model.token_emb[tok] -= lr * d_final[b, t]

    return loss


if __name__ == "__main__":
    print("Lloyd's Tiny Transformer — pure scratch + learning")
    print("-------------------------------------------------")

    model = TinyTransformer(
        vocab_size=64,
        d_model=32,
        n_layers=2,
        n_heads=4,
        d_ff=64,
        max_seq_len=32,
    )

    # Fake data
    batch_x = np.random.randint(0, 64, size=(8, 12))
    batch_y = np.random.randint(0, 64, size=(8, 12))

    print("Forward shape:", model.forward(batch_x).shape)
    print()

    print("Training...")
    for step in range(30):
        loss = train_step(model, batch_x, batch_y, lr=0.01)
        if step % 5 == 0:
            print(f"Step {step:02d} | loss = {loss:.4f}")

    print("\nGeneration test after learning:")
    generated = model.generate([1, 2, 3], max_new_tokens=12)
    print(generated)
