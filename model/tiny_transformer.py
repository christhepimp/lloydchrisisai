"""
Lloyd's Pure-Scratch Tiny Transformer
=====================================
Decoder-only Transformer written from absolute zero.
No PyTorch, no TensorFlow, no Hugging Face — only NumPy.

This is the seed architecture. We will scale it toward 3B later.
"""

import numpy as np
from typing import List, Tuple, Optional


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(x)
    return e / np.sum(e, axis=axis, keepdims=True)


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

        # Weights (simple random init)
        self.W_q = np.random.randn(d_model, d_model) * 0.02
        self.W_k = np.random.randn(d_model, d_model) * 0.02
        self.W_v = np.random.randn(d_model, d_model) * 0.02
        self.W_o = np.random.randn(d_model, d_model) * 0.02

    def forward(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        batch, seq_len, _ = x.shape

        Q = x @ self.W_q
        K = x @ self.W_k
        V = x @ self.W_v

        # Reshape to (batch, n_heads, seq_len, d_k)
        Q = Q.reshape(batch, seq_len, self.n_heads, self.d_k).transpose(0, 2, 1, 3)
        K = K.reshape(batch, seq_len, self.n_heads, self.d_k).transpose(0, 2, 1, 3)
        V = V.reshape(batch, seq_len, self.n_heads, self.d_k).transpose(0, 2, 1, 3)

        # Scaled dot-product attention
        scores = (Q @ K.transpose(0, 1, 3, 2)) / np.sqrt(self.d_k)

        if mask is not None:
            scores = np.where(mask == 0, -1e9, scores)

        attn = softmax(scores, axis=-1)
        out = attn @ V

        # Back to (batch, seq_len, d_model)
        out = out.transpose(0, 2, 1, 3).reshape(batch, seq_len, self.d_model)
        return out @ self.W_o


class FeedForward:
    def __init__(self, d_model: int, d_ff: int):
        self.W1 = np.random.randn(d_model, d_ff) * 0.02
        self.b1 = np.zeros(d_ff)
        self.W2 = np.random.randn(d_ff, d_model) * 0.02
        self.b2 = np.zeros(d_model)

    def forward(self, x: np.ndarray) -> np.ndarray:
        return (np.maximum(0, x @ self.W1 + self.b1) @ self.W2) + self.b2


class TransformerBlock:
    def __init__(self, d_model: int, n_heads: int, d_ff: int):
        self.attn = MultiHeadAttention(d_model, n_heads)
        self.ffn = FeedForward(d_model, d_ff)

    def forward(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        # Pre-norm style
        x = x + self.attn.forward(layer_norm(x), mask)
        x = x + self.ffn.forward(layer_norm(x))
        return x


class TinyTransformer:
    """
    Decoder-only Transformer — Lloyd's first brain.
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

        # Token + positional embeddings
        self.token_emb = np.random.randn(vocab_size, d_model) * 0.02
        self.pos_emb = self._sinusoidal_positional_encoding(max_seq_len, d_model)

        # Transformer blocks
        self.blocks = [
            TransformerBlock(d_model, n_heads, d_ff) for _ in range(n_layers)
        ]

        # Output projection
        self.W_out = np.random.randn(d_model, vocab_size) * 0.02

    def _sinusoidal_positional_encoding(self, max_len: int, d_model: int) -> np.ndarray:
        pe = np.zeros((max_len, d_model))
        position = np.arange(0, max_len)[:, np.newaxis]
        div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))
        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)
        return pe

    def _causal_mask(self, seq_len: int) -> np.ndarray:
        mask = np.tril(np.ones((seq_len, seq_len)))
        return mask[np.newaxis, np.newaxis, :, :]  # (1, 1, seq, seq)

    def forward(self, token_ids: np.ndarray) -> np.ndarray:
        """
        token_ids: (batch, seq_len) integers
        returns logits: (batch, seq_len, vocab_size)
        """
        batch, seq_len = token_ids.shape
        assert seq_len <= self.max_seq_len

        x = self.token_emb[token_ids] + self.pos_emb[:seq_len]
        mask = self._causal_mask(seq_len)

        for block in self.blocks:
            x = block.forward(x, mask)

        x = layer_norm(x)
        logits = x @ self.W_out
        return logits

    def generate(self, start_ids: List[int], max_new_tokens: int = 20) -> List[int]:
        ids = list(start_ids)
        for _ in range(max_new_tokens):
            x = np.array([ids[-self.max_seq_len:]])
            logits = self.forward(x)
            next_id = int(np.argmax(logits[0, -1]))
            ids.append(next_id)
        return ids


def cross_entropy_loss(logits: np.ndarray, targets: np.ndarray) -> float:
    """
    logits: (batch, seq, vocab)
    targets: (batch, seq)
    """
    batch, seq, vocab = logits.shape
    logits_flat = logits.reshape(-1, vocab)
    targets_flat = targets.reshape(-1)

    probs = softmax(logits_flat, axis=-1)
    # Gather the probabilities of the correct tokens
    correct = probs[np.arange(len(targets_flat)), targets_flat]
    loss = -np.mean(np.log(correct + 1e-9))
    return float(loss)


def train_step(model: TinyTransformer, batch_x: np.ndarray, batch_y: np.ndarray, lr: float = 1e-3):
    """
    Extremely simple training step (no real backprop yet — just a placeholder
    that shows the loop structure). Real gradients will be added next.
    """
    logits = model.forward(batch_x)
    loss = cross_entropy_loss(logits, batch_y)

    # TODO: real backpropagation will be implemented here
    # For now we just return the loss so the loop can run
    return loss


if __name__ == "__main__":
    print("Lloyd's Tiny Transformer — pure scratch")
    print("---------------------------------------")

    model = TinyTransformer(
        vocab_size=64,
        d_model=32,
        n_layers=2,
        n_heads=4,
        d_ff=64,
        max_seq_len=32,
    )

    # Fake data for demo
    batch_x = np.random.randint(0, 64, size=(4, 16))
    batch_y = np.random.randint(0, 64, size=(4, 16))

    print("Forward pass shape:", model.forward(batch_x).shape)

    for step in range(5):
        loss = train_step(model, batch_x, batch_y)
        print(f"Step {step:02d} | loss = {loss:.4f}")

    print("\nGeneration test:")
    generated = model.generate([1, 2, 3], max_new_tokens=10)
    print(generated)
