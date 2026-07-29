"""
Lloyd's Pure-Scratch Image Generator
====================================
Text-conditioned image model written from absolute zero.
No Stable Diffusion, no APIs, no PyTorch — only NumPy.

Architecture (original):
  prompt chars → bag embedding → MLP + noise → HxWx3 pixels in [0,1]

Trainable via train_step on simple reconstruction targets.
Portable via save() / load() into the same .lloyd brain later.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import json
import zlib
import struct
import base64


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def _text_embed(prompt: str, dim: int = 64) -> np.ndarray:
    """Pure-scratch bag-of-chars embedding (deterministic)."""
    v = np.zeros(dim, dtype=np.float64)
    if not prompt:
        return v
    for i, ch in enumerate(prompt.lower()):
        idx = (ord(ch) * 131 + i * 17) % dim
        v[idx] += 1.0
    n = np.linalg.norm(v)
    if n > 1e-8:
        v /= n
    return v


class TinyImageNet:
    """
    Lloyd's original image brain.
    Maps (text_embed, noise) → RGB image via a small MLP.
    """

    def __init__(
        self,
        text_dim: int = 64,
        noise_dim: int = 32,
        hidden: int = 256,
        height: int = 64,
        width: int = 64,
    ):
        self.text_dim = text_dim
        self.noise_dim = noise_dim
        self.hidden = hidden
        self.height = height
        self.width = width
        self.out_dim = height * width * 3
        in_dim = text_dim + noise_dim

        scale = 0.05
        self.W1 = np.random.randn(in_dim, hidden) * scale
        self.b1 = np.zeros(hidden)
        self.W2 = np.random.randn(hidden, hidden) * scale
        self.b2 = np.zeros(hidden)
        self.W3 = np.random.randn(hidden, self.out_dim) * (scale * 0.5)
        self.b3 = np.zeros(self.out_dim)

        # color bias so early images aren't pure gray noise
        self.b3[0::3] += 0.15  # R
        self.b3[1::3] += 0.12  # G
        self.b3[2::3] += 0.25  # B-ish

    def forward(self, text_emb: np.ndarray, noise: np.ndarray) -> np.ndarray:
        """Return image as float array (H, W, 3) in [0, 1]."""
        x = np.concatenate([text_emb, noise])
        h1 = _relu(x @ self.W1 + self.b1)
        h2 = _relu(h1 @ self.W2 + self.b2)
        raw = h2 @ self.W3 + self.b3
        img = _sigmoid(raw).reshape(self.height, self.width, 3)
        return img

    def generate(self, prompt: str, seed: Optional[int] = None) -> np.ndarray:
        if seed is not None:
            rng = np.random.RandomState(seed)
            noise = rng.randn(self.noise_dim)
        else:
            noise = np.random.randn(self.noise_dim)
        text = _text_embed(prompt, self.text_dim)
        return self.forward(text, noise)

    def train_step(
        self,
        prompt: str,
        target: np.ndarray,
        lr: float = 1e-3,
    ) -> float:
        """
        One supervised step toward a target image (H,W,3) in [0,1].
        Pure NumPy backprop through the MLP + sigmoid.
        """
        text = _text_embed(prompt, self.text_dim)
        noise = np.random.randn(self.noise_dim) * 0.1  # mild noise while training
        x = np.concatenate([text, noise])

        # forward with cache
        z1 = x @ self.W1 + self.b1
        h1 = _relu(z1)
        z2 = h1 @ self.W2 + self.b2
        h2 = _relu(z2)
        z3 = h2 @ self.W3 + self.b3
        pred_flat = _sigmoid(z3)
        target_flat = target.reshape(-1).astype(np.float64)

        # MSE
        diff = pred_flat - target_flat
        loss = float(np.mean(diff ** 2))

        # dL/dz3 through sigmoid
        d_pred = (2.0 / pred_flat.size) * diff
        d_z3 = d_pred * pred_flat * (1.0 - pred_flat)

        d_W3 = np.outer(h2, d_z3)
        d_b3 = d_z3
        d_h2 = d_z3 @ self.W3.T
        d_z2 = d_h2 * (z2 > 0)
        d_W2 = np.outer(h1, d_z2)
        d_b2 = d_z2
        d_h1 = d_z2 @ self.W2.T
        d_z1 = d_h1 * (z1 > 0)
        d_W1 = np.outer(x, d_z1)
        d_b1 = d_z1

        self.W3 -= lr * d_W3
        self.b3 -= lr * d_b3
        self.W2 -= lr * d_W2
        self.b2 -= lr * d_b2
        self.W1 -= lr * d_W1
        self.b1 -= lr * d_b1

        return loss

    def get_state(self) -> dict:
        return {
            "config": {
                "text_dim": self.text_dim,
                "noise_dim": self.noise_dim,
                "hidden": self.hidden,
                "height": self.height,
                "width": self.width,
            },
            "W1": self.W1,
            "b1": self.b1,
            "W2": self.W2,
            "b2": self.b2,
            "W3": self.W3,
            "b3": self.b3,
        }

    def set_state(self, state: dict):
        cfg = state["config"]
        if cfg["height"] != self.height or cfg["width"] != self.width:
            raise ValueError("Image net size mismatch")
        self.W1 = state["W1"]
        self.b1 = state["b1"]
        self.W2 = state["W2"]
        self.b2 = state["b2"]
        self.W3 = state["W3"]
        self.b3 = state["b3"]

    def save(self, path: str | Path):
        path = Path(path)
        st = self.get_state()
        np.savez_compressed(
            path,
            config=json.dumps(st["config"]),
            W1=st["W1"],
            b1=st["b1"],
            W2=st["W2"],
            b2=st["b2"],
            W3=st["W3"],
            b3=st["b3"],
        )

    def load(self, path: str | Path):
        path = Path(path)
        data = np.load(path, allow_pickle=False)
        state = {
            "config": json.loads(str(data["config"])),
            "W1": data["W1"],
            "b1": data["b1"],
            "W2": data["W2"],
            "b2": data["b2"],
            "W3": data["W3"],
            "b3": data["b3"],
        }
        self.set_state(state)


def rgb_to_png_bytes(img: np.ndarray) -> bytes:
    """Minimal PNG encoder (no PIL). img: HxWx3 float [0,1] or uint8."""
    if img.dtype != np.uint8:
        arr = np.clip(img * 255.0, 0, 255).astype(np.uint8)
    else:
        arr = img
    h, w, c = arr.shape
    assert c == 3

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b""
    for y in range(h):
        raw += b"\x00" + arr[y].tobytes()

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    return png


def image_to_data_uri(img: np.ndarray) -> str:
    png = rgb_to_png_bytes(img)
    b64 = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"


if __name__ == "__main__":
    net = TinyImageNet(height=32, width=32, hidden=128)
    img = net.generate("neon city at night", seed=42)
    print("shape", img.shape, "min/max", img.min(), img.max())
    uri = image_to_data_uri(img)
    print("data uri length", len(uri))
    # fake train toward a solid color
    target = np.zeros((32, 32, 3))
    target[..., 0] = 0.9
    target[..., 2] = 0.4
    for i in range(20):
        loss = net.train_step("red vibe", target, lr=0.05)
        if i % 5 == 0:
            print(f"step {i} loss {loss:.4f}")
    print("TinyImageNet OK")
