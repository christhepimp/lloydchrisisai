"""
Lloyd Image Pattern Learning Model
==================================
Hardcodes 100 synthetic uncanny-valley + mature-abstract images as
exact numerical pixel arrays (64x64x3).

Training teaches:
  - exact pixel values
  - which pixels belong together
  - color pairing and spatial structure
  - mathematical patterns that make an image coherent

After training the net can generate, interpolate, and vary images
from the learned math (not simple averaging).

Pure NumPy. No external image APIs or photo files.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import json

from model.tiny_image import TinyImageNet, image_to_data_uri


# ---------------------------------------------------------------------------
# Deterministic procedural generators → exact fixed pixel arrays
# ---------------------------------------------------------------------------

def _rng(seed: int) -> np.random.RandomState:
    return np.random.RandomState(seed)


def _skin_tone(rng: np.random.RandomState) -> np.ndarray:
    """Range of realistic-ish skin tones (abstract)."""
    base = np.array([0.78, 0.58, 0.48], dtype=np.float64)
    base += rng.randn(3) * 0.08
    return np.clip(base, 0.25, 0.95)


def _make_uncanny_face(h: int, w: int, seed: int, intensity: float = 1.0) -> np.ndarray:
    """Distorted face / doll / uncanny valley target."""
    rng = _rng(seed)
    img = np.zeros((h, w, 3), dtype=np.float64)

    # background
    bg = rng.uniform(0.05, 0.25, 3)
    img[:] = bg

    # head ellipse (slightly wrong proportions)
    cy = 0.42 + rng.uniform(-0.04, 0.04)
    cx = 0.5 + rng.uniform(-0.03, 0.03)
    ry = 0.32 + rng.uniform(-0.05, 0.06)
    rx = 0.26 + rng.uniform(-0.04, 0.05)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    yy /= max(h - 1, 1)
    xx /= max(w - 1, 1)

    head = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    mask = head < 1.0
    skin = _skin_tone(rng)
    for c in range(3):
        img[..., c] = np.where(mask, skin[c] * (0.85 + 0.15 * (1 - head)), img[..., c])

    # eyes – deliberately off (dead / too close / different sizes)
    eye_y = cy - 0.08 + rng.uniform(-0.03, 0.03)
    eye_sep = 0.11 + rng.uniform(-0.04, 0.05)
    eye_r = 0.045 + rng.uniform(-0.015, 0.02)

    for i, side in enumerate((-1, 1)):
        ex = cx + side * eye_sep
        er = eye_r * (1.0 + side * rng.uniform(-0.25, 0.25))
        ed = np.sqrt((xx - ex) ** 2 + (yy - eye_y) ** 2)
        eye = ed < er
        # dark sclera / dead look
        img[..., 0] = np.where(eye, 0.12 + rng.uniform(0, 0.08), img[..., 0])
        img[..., 1] = np.where(eye, 0.10 + rng.uniform(0, 0.06), img[..., 1])
        img[..., 2] = np.where(eye, 0.18 + rng.uniform(0, 0.1), img[..., 2])
        # tiny bright pupil (wrong placement)
        pupil = ed < er * 0.35
        img[..., :] = np.where(pupil[..., None], 0.02, img)

    # mouth – too wide / wrong height / plastic
    mouth_y = cy + 0.14 + rng.uniform(-0.03, 0.04)
    mouth_w = 0.12 + rng.uniform(0.0, 0.08)
    mouth = np.exp(-((xx - cx) ** 2 / (mouth_w ** 2) + (yy - mouth_y) ** 2 / 0.008))
    mouth_mask = mouth > 0.3
    img[..., 0] = np.where(mouth_mask, np.minimum(img[..., 0] + 0.25, 0.9), img[..., 0])
    img[..., 1] = np.where(mouth_mask, img[..., 1] * 0.6, img[..., 1])
    img[..., 2] = np.where(mouth_mask, img[..., 2] * 0.55, img[..., 2])

    # slight plastic sheen
    sheen = np.exp(-((xx - cx - 0.05) ** 2 + (yy - cy + 0.1) ** 2) * 18)
    img = np.clip(img + sheen[..., None] * 0.12 * intensity, 0, 1)

    # noise for texture
    img += rng.randn(h, w, 3) * 0.012
    return np.clip(img, 0, 1)


def _make_body_abstract(h: int, w: int, seed: int) -> np.ndarray:
    """Abstract body / torso + limbs with mature color palette (non-photographic)."""
    rng = _rng(seed)
    img = np.zeros((h, w, 3), dtype=np.float64)
    bg = rng.uniform(0.04, 0.18, 3)
    img[:] = bg

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    yy /= max(h - 1, 1)
    xx /= max(w - 1, 1)

    skin = _skin_tone(rng)

    # torso ellipse
    cy, cx = 0.55, 0.5
    torso = ((xx - cx) / 0.22) ** 2 + ((yy - cy) / 0.28) ** 2 < 1.0
    for c in range(3):
        img[..., c] = np.where(torso, skin[c], img[..., c])

    # head blob
    head = ((xx - 0.5) / 0.14) ** 2 + ((yy - 0.22) / 0.14) ** 2 < 1.0
    for c in range(3):
        img[..., c] = np.where(head, skin[c] * 0.95, img[..., c])

    # limb-like soft cylinders (abstract)
    for side in (-1, 1):
        # arms
        arm = np.exp(-((xx - (0.5 + side * 0.28)) ** 2 * 40 + (yy - 0.48) ** 2 * 8))
        img = np.clip(img + arm[..., None] * skin * 0.7, 0, 1)
        # legs
        leg = np.exp(-((xx - (0.5 + side * 0.12)) ** 2 * 55 + (yy - 0.82) ** 2 * 6))
        img = np.clip(img + leg[..., None] * skin * 0.65, 0, 1)

    img += rng.randn(h, w, 3) * 0.01
    return np.clip(img, 0, 1)


def _make_pattern_field(h: int, w: int, seed: int) -> np.ndarray:
    """Repeating spatial patterns, color pairing, edge structure."""
    rng = _rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    yy /= max(h - 1, 1)
    xx /= max(w - 1, 1)

    freq = rng.uniform(3, 9)
    phase = rng.uniform(0, 6.28)
    base = 0.5 + 0.35 * np.sin(freq * np.pi * xx + phase) * np.cos(freq * 0.7 * np.pi * yy)

    c1 = rng.uniform(0.2, 0.9, 3)
    c2 = rng.uniform(0.1, 0.7, 3)
    img = base[..., None] * c1 + (1 - base[..., None]) * c2

    # add a few hard edges
    if rng.rand() > 0.4:
        edge = (xx > rng.uniform(0.3, 0.7)).astype(np.float64)
        img = img * (0.7 + 0.3 * edge[..., None])

    img += rng.randn(h, w, 3) * 0.015
    return np.clip(img, 0, 1)


def _make_creepy_doll(h: int, w: int, seed: int) -> np.ndarray:
    """Strong uncanny valley doll."""
    face = _make_uncanny_face(h, w, seed, intensity=1.3)
    rng = _rng(seed + 999)
    # flatten colors toward porcelain
    face = face * 0.75 + np.array([0.85, 0.78, 0.75]) * 0.25
    # crack lines
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64) / max(h - 1, 1)
    for _ in range(rng.randint(2, 5)):
        ang = rng.uniform(0, 3.14)
        crack = np.abs((xx - 0.5) * np.cos(ang) + (yy - 0.4) * np.sin(ang)) < 0.008
        face[crack] *= 0.55
    return np.clip(face, 0, 1)


def build_hardcoded_dataset(height: int = 64, width: int = 64, n: int = 100) -> List[Tuple[str, np.ndarray]]:
    """
    Returns list of (prompt, pixel_array) where pixel_array is the exact
    hardcoded numerical values. Deterministic across runs.
    """
    dataset = []
    generators = [
        ("uncanny face distorted eyes", _make_uncanny_face),
        ("creepy porcelain doll face", _make_creepy_doll),
        ("abstract mature body form", _make_body_abstract),
        ("repeating color pattern field", _make_pattern_field),
    ]

    for i in range(n):
        gen_idx = i % len(generators)
        name, fn = generators[gen_idx]
        seed = 1000 + i * 17 + gen_idx * 31
        if fn is _make_uncanny_face or fn is _make_creepy_doll:
            img = fn(height, width, seed)
        else:
            img = fn(height, width, seed)
        prompt = f"{name} variant {i}"
        dataset.append((prompt, img.astype(np.float64)))
    return dataset


# ---------------------------------------------------------------------------
# Pattern Learner – trains TinyImageNet on the 100 hardcoded arrays
# ---------------------------------------------------------------------------

class ImagePatternLearner:
    def __init__(self, height: int = 64, width: int = 64, hidden: int = 384):
        self.height = height
        self.width = width
        self.net = TinyImageNet(height=height, width=width, hidden=hidden)
        self.dataset: List[Tuple[str, np.ndarray]] = []
        self.trained = False
        self.train_log: List[Dict[str, Any]] = []

    def load_hardcoded_images(self, n: int = 100):
        """Store the 100 images as numerical arrays in model memory."""
        self.dataset = build_hardcoded_dataset(self.height, self.width, n=n)
        return len(self.dataset)

    def train(self, epochs: int = 100, lr: float = 0.015, log_every: int = 10) -> Dict[str, Any]:
        """
        Simple training loop over the hardcoded pixel arrays.
        Main learning signal = image mathematics (MSE on residual path).
        """
        if not self.dataset:
            self.load_hardcoded_images()

        n = len(self.dataset)
        history = []
        for ep in range(epochs):
            ep_loss = 0.0
            # shuffle order each epoch so it learns patterns, not sequence
            order = np.random.permutation(n)
            for idx in order:
                prompt, target = self.dataset[idx]
                loss = self.net.train_step(prompt, target, lr=lr)
                ep_loss += loss
            avg = ep_loss / n
            history.append(avg)
            if (ep + 1) % log_every == 0 or ep == 0:
                self.train_log.append({"epoch": ep + 1, "avg_loss": float(avg)})
                print(f"epoch {ep+1:3d}/{epochs}  avg_loss={avg:.5f}")

        self.trained = True
        return {
            "epochs": epochs,
            "images": n,
            "final_loss": float(history[-1]),
            "start_loss": float(history[0]),
            "message": f"trained {epochs} epochs on {n} hardcoded pixel arrays",
        }

    def generate(self, prompt: str, seed: Optional[int] = None) -> np.ndarray:
        return self.net.generate(prompt, seed=seed)

    def interpolate(self, idx_a: int, idx_b: int, alpha: float = 0.5, prompt: str = "blend") -> np.ndarray:
        """Blend two learned targets in pixel space then let the net refine."""
        if not self.dataset:
            self.load_hardcoded_images()
        a = self.dataset[idx_a % len(self.dataset)][1]
        b = self.dataset[idx_b % len(self.dataset)][1]
        target = np.clip((1 - alpha) * a + alpha * b, 0, 1)
        # quick adaptation steps so the net internalizes the blend
        for _ in range(8):
            self.net.train_step(prompt, target, lr=0.01)
        return self.net.generate(prompt, seed=42)

    def variation(self, base_idx: int, strength: float = 0.25, prompt: Optional[str] = None) -> np.ndarray:
        """Create a variation of a stored pattern."""
        if not self.dataset:
            self.load_hardcoded_images()
        p, base = self.dataset[base_idx % len(self.dataset)]
        prompt = prompt or p
        noise = np.random.randn(*base.shape) * strength * 0.08
        target = np.clip(base + noise, 0, 1)
        for _ in range(6):
            self.net.train_step(prompt, target, lr=0.012)
        return self.net.generate(prompt)

    def pixel_stats(self, idx: int = 0) -> Dict[str, Any]:
        """Answer questions about pixel positions / patterns of a stored image."""
        if not self.dataset:
            self.load_hardcoded_images()
        _, img = self.dataset[idx % len(self.dataset)]
        return {
            "shape": list(img.shape),
            "mean_rgb": [float(x) for x in img.mean(axis=(0, 1))],
            "std_rgb": [float(x) for x in img.std(axis=(0, 1))],
            "min": float(img.min()),
            "max": float(img.max()),
            "center_pixel": [float(x) for x in img[img.shape[0]//2, img.shape[1]//2]],
        }

    def save(self, path: str | Path):
        self.net.save(path)

    def load(self, path: str | Path):
        self.net.load(path)
        self.trained = True

    def get_dataset_preview(self, k: int = 5) -> List[Dict[str, Any]]:
        """Return a few of the hardcoded arrays as data-URIs for inspection."""
        if not self.dataset:
            self.load_hardcoded_images()
        out = []
        for i in range(min(k, len(self.dataset))):
            p, arr = self.dataset[i]
            out.append({
                "index": i,
                "prompt": p,
                "image": image_to_data_uri(arr),
                "mean_rgb": [float(x) for x in arr.mean(axis=(0, 1))],
            })
        return out


# convenience singleton for Lloyd
pattern_learner = ImagePatternLearner()
