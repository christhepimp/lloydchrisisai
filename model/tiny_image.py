"""
Lloyd's Pure-Scratch Image Generator v2
=========================================
Text-conditioned spatial generator — NumPy only.

Pipeline:
  prompt → embedding + keyword scene bias
  → MLP latent grid (h x w x c)
  → local spatial mix (original "soft conv")
  → RGB 64x64

Still fully original. No diffusion APIs.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Optional
import json
import zlib
import struct
import base64


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def _text_embed(prompt: str, dim: int = 96) -> np.ndarray:
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


# Original keyword → color/atmosphere prior (not copied art — engineered priors)
SCENE_PRIORS = [
    (("neon", "city", "night", "cyber"), (0.15, 0.05, 0.45), (0.95, 0.2, 0.85)),
    (("sunset", "ocean", "beach", "wave"), (0.95, 0.45, 0.15), (0.2, 0.35, 0.75)),
    (("forest", "tree", "green", "nature"), (0.1, 0.35, 0.1), (0.2, 0.7, 0.25)),
    (("fire", "lava", "red", "magma"), (0.5, 0.05, 0.0), (1.0, 0.4, 0.05)),
    (("robot", "lloyd", "face", "android"), (0.25, 0.28, 0.32), (0.1, 0.9, 0.7)),
    (("uncanny", "creepy", "valley", "doll"), (0.55, 0.45, 0.4), (0.35, 0.3, 0.35)),
    (("space", "star", "galaxy", "void"), (0.02, 0.02, 0.08), (0.7, 0.7, 1.0)),
    (("wolf", "mountain", "snow"), (0.35, 0.4, 0.45), (0.85, 0.85, 0.9)),
]


def _scene_bias(prompt: str, h: int, w: int) -> np.ndarray:
    """Build a soft spatial color field from keywords + geometry (original)."""
    lower = prompt.lower()
    base = np.array([0.2, 0.18, 0.28], dtype=np.float64)
    accent = np.array([0.5, 0.45, 0.7], dtype=np.float64)
    for keys, b, a in SCENE_PRIORS:
        if any(k in lower for k in keys):
            base = np.array(b, dtype=np.float64)
            accent = np.array(a, dtype=np.float64)
            break

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    yy /= max(h - 1, 1)
    xx /= max(w - 1, 1)

    img = np.zeros((h, w, 3), dtype=np.float64)
    # vertical gradient sky/ground
    for c in range(3):
        img[..., c] = base[c] * (1 - yy) + accent[c] * yy * 0.5 + base[c] * 0.3

    # center glow / "subject" blob
    cx, cy = 0.5, 0.45
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    blob = np.exp(-dist * dist * 8.0)
    for c in range(3):
        img[..., c] = img[..., c] * (1 - 0.55 * blob) + accent[c] * blob

    # face-like prior for robot/uncanny
    if any(k in lower for k in ("face", "robot", "lloyd", "uncanny", "doll")):
        eye_y, eye_x1, eye_x2 = 0.38, 0.35, 0.65
        for ex in (eye_x1, eye_x2):
            ed = np.sqrt((xx - ex) ** 2 + (yy - eye_y) ** 2)
            eye = np.exp(-ed * ed * 90.0)
            img[..., 0] = np.minimum(img[..., 0], 1 - 0.7 * eye)
            img[..., 1] = np.minimum(img[..., 1], 1 - 0.5 * eye)
            img[..., 2] = np.minimum(img[..., 2] + 0.5 * eye, 1.0)
        mouth = np.exp(-((xx - 0.5) ** 2 * 40 + (yy - 0.62) ** 2 * 120))
        img[..., 0] = np.minimum(img[..., 0] + 0.2 * mouth, 1.0)

    return np.clip(img, 0, 1)


def _spatial_mix(grid: np.ndarray) -> np.ndarray:
    """3x3 average mix — pure NumPy local structure (soft conv)."""
    h, w, c = grid.shape
    out = grid.copy()
    padded = np.pad(grid, ((1, 1), (1, 1), (0, 0)), mode="edge")
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            out += padded[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w] * 0.08
    return out / (1.0 + 0.08 * 8)


class TinyImageNet:
    def __init__(
        self,
        text_dim: int = 96,
        noise_dim: int = 48,
        hidden: int = 384,
        height: int = 64,
        width: int = 64,
        grid: int = 16,
        channels: int = 32,
    ):
        self.text_dim = text_dim
        self.noise_dim = noise_dim
        self.hidden = hidden
        self.height = height
        self.width = width
        self.grid = grid
        self.channels = channels
        self.latent_dim = grid * grid * channels
        in_dim = text_dim + noise_dim

        scale = 0.04
        self.W1 = np.random.randn(in_dim, hidden) * scale
        self.b1 = np.zeros(hidden)
        self.W2 = np.random.randn(hidden, hidden) * scale
        self.b2 = np.zeros(hidden)
        self.W3 = np.random.randn(hidden, self.latent_dim) * (scale * 0.5)
        self.b3 = np.zeros(self.latent_dim)
        # project channels → RGB at each grid cell
        self.W_rgb = np.random.randn(channels, 3) * scale
        self.b_rgb = np.array([0.2, 0.18, 0.25])

    def _upsample(self, small: np.ndarray) -> np.ndarray:
        """Nearest-neighbor upsample grid → full res."""
        gh, gw, c = small.shape
        y_idx = (np.linspace(0, gh - 1, self.height)).astype(int)
        x_idx = (np.linspace(0, gw - 1, self.width)).astype(int)
        return small[y_idx][:, x_idx]

    def forward(self, text_emb: np.ndarray, noise: np.ndarray, prompt: str = "") -> np.ndarray:
        x = np.concatenate([text_emb, noise])
        h1 = _relu(x @ self.W1 + self.b1)
        h2 = _relu(h1 @ self.W2 + self.b2)
        latent = h2 @ self.W3 + self.b3
        grid = latent.reshape(self.grid, self.grid, self.channels)
        grid = _spatial_mix(grid)
        grid = _spatial_mix(grid)
        rgb_small = _sigmoid(grid @ self.W_rgb + self.b_rgb)
        rgb = self._upsample(rgb_small)
        # blend engineered scene prior (structure) with learned residual
        prior = _scene_bias(prompt, self.height, self.width)
        img = np.clip(0.55 * prior + 0.45 * rgb, 0, 1)
        return img

    def generate(self, prompt: str, seed: Optional[int] = None) -> np.ndarray:
        if seed is not None:
            rng = np.random.RandomState(seed)
            noise = rng.randn(self.noise_dim)
        else:
            noise = np.random.randn(self.noise_dim)
        text = _text_embed(prompt, self.text_dim)
        return self.forward(text, noise, prompt=prompt)

    def train_step(self, prompt: str, target: np.ndarray, lr: float = 1e-3) -> float:
        text = _text_embed(prompt, self.text_dim)
        noise = np.random.randn(self.noise_dim) * 0.15
        x = np.concatenate([text, noise])

        z1 = x @ self.W1 + self.b1
        h1 = _relu(z1)
        z2 = h1 @ self.W2 + self.b2
        h2 = _relu(z2)
        z3 = h2 @ self.W3 + self.b3
        grid = z3.reshape(self.grid, self.grid, self.channels)
        grid_m = _spatial_mix(_spatial_mix(grid))
        rgb_small = _sigmoid(grid_m @ self.W_rgb + self.b_rgb)
        pred = self._upsample(rgb_small)
        prior = _scene_bias(prompt, self.height, self.width)
        pred_blend = np.clip(0.55 * prior + 0.45 * pred, 0, 1)

        diff = pred_blend - target.astype(np.float64)
        loss = float(np.mean(diff ** 2))

        # backprop mainly into residual path (approx)
        d_pred = (2.0 / diff.size) * diff * 0.45
        # downsample grad roughly
        factor_y = self.height // self.grid
        factor_x = self.width // self.grid
        d_small = np.zeros_like(rgb_small)
        for iy in range(self.grid):
            for ix in range(self.grid):
                block = d_pred[
                    iy * factor_y : (iy + 1) * factor_y,
                    ix * factor_x : (ix + 1) * factor_x,
                ]
                d_small[iy, ix] = block.mean(axis=(0, 1))

        d_z_rgb = d_small * rgb_small * (1 - rgb_small)
        flat_g = grid_m.reshape(-1, self.channels)
        d_flat = d_z_rgb.reshape(-1, 3)
        d_W_rgb = flat_g.T @ d_flat
        d_b_rgb = d_flat.sum(axis=0)
        d_grid = (d_flat @ self.W_rgb.T).reshape(self.grid, self.grid, self.channels)
        d_latent = d_grid.reshape(-1)

        d_W3 = np.outer(h2, d_latent)
        d_b3 = d_latent
        d_h2 = d_latent @ self.W3.T
        d_z2 = d_h2 * (z2 > 0)
        d_W2 = np.outer(h1, d_z2)
        d_b2 = d_z2
        d_h1 = d_z2 @ self.W2.T
        d_z1 = d_h1 * (z1 > 0)
        d_W1 = np.outer(x, d_z1)
        d_b1 = d_z1

        self.W_rgb -= lr * d_W_rgb
        self.b_rgb -= lr * d_b_rgb
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
                "grid": self.grid,
                "channels": self.channels,
                "version": 2,
            },
            "W1": self.W1,
            "b1": self.b1,
            "W2": self.W2,
            "b2": self.b2,
            "W3": self.W3,
            "b3": self.b3,
            "W_rgb": self.W_rgb,
            "b_rgb": self.b_rgb,
        }

    def set_state(self, state: dict):
        self.W1 = state["W1"]
        self.b1 = state["b1"]
        self.W2 = state["W2"]
        self.b2 = state["b2"]
        self.W3 = state["W3"]
        self.b3 = state["b3"]
        self.W_rgb = state["W_rgb"]
        self.b_rgb = state["b_rgb"]

    def save(self, path: str | Path):
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
            W_rgb=st["W_rgb"],
            b_rgb=st["b_rgb"],
        )

    def load(self, path: str | Path):
        data = np.load(path, allow_pickle=False)
        cfg = json.loads(str(data["config"]))
        if cfg.get("version", 1) < 2:
            raise ValueError("Old image net v1 weights — retrain for v2")
        self.set_state(
            {
                "W1": data["W1"],
                "b1": data["b1"],
                "W2": data["W2"],
                "b2": data["b2"],
                "W3": data["W3"],
                "b3": data["b3"],
                "W_rgb": data["W_rgb"],
                "b_rgb": data["b_rgb"],
            }
        )


def rgb_to_png_bytes(img: np.ndarray) -> bytes:
    if img.dtype != np.uint8:
        arr = np.clip(img * 255.0, 0, 255).astype(np.uint8)
    else:
        arr = img
    h, w, c = arr.shape

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b""
    for y in range(h):
        raw += b"\x00" + arr[y].tobytes()
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    return png


def image_to_data_uri(img: np.ndarray) -> str:
    b64 = base64.b64encode(rgb_to_png_bytes(img)).decode("ascii")
    return f"data:image/png;base64,{b64}"
