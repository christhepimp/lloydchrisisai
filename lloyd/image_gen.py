"""
Lloyd's Image Generation — pure original
=========================================
Uses model.tiny_image.TinyImageNet (NumPy only).
Optionally backed by ImagePatternLearner (100 hardcoded pixel arrays).
No external image APIs. Real PNG pixels.
"""

from __future__ import annotations

import random
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from model.tiny_image import TinyImageNet, image_to_data_uri

try:
    from model.image_pattern_learner import ImagePatternLearner, pattern_learner
except Exception:
    ImagePatternLearner = None
    pattern_learner = None


class ImageGenerator:
    def __init__(self, height: int = 64, width: int = 64):
        self.net = TinyImageNet(height=height, width=width, hidden=256)
        self.history = []
        self.height = height
        self.width = width
        self.pattern = pattern_learner  # may be None if import failed

    def generate(self, prompt: str, autonomous: bool = False) -> Dict[str, Any]:
        """
        Generate a real image from prompt. Returns dict with:
          - message: text for chat
          - image: data URI (PNG base64) for the UI
          - id, prompt, autonomous
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_id = f"lloyd_img_{timestamp}_{random.randint(1000, 9999)}"

        # strip trigger words so the net sees the subject
        clean = prompt
        for w in ("image", "picture", "photo", "generate", "draw", "create art", "of", "a", "an", "the"):
            clean = clean.replace(w, " ").replace(w.upper(), " ")
        clean = " ".join(clean.split()) or prompt

        seed = abs(hash(clean + timestamp)) % (2**31)

        # prefer pattern learner if it has been trained
        if self.pattern is not None and getattr(self.pattern, "trained", False):
            pixels = self.pattern.generate(clean, seed=seed)
        else:
            pixels = self.net.generate(clean, seed=seed)

        data_uri = image_to_data_uri(pixels)

        result = {
            "id": img_id,
            "prompt": prompt,
            "clean_prompt": clean,
            "status": "ok",
            "autonomous": autonomous,
            "image": data_uri,
            "message": (
                f"cooked this for you\n"
                f"prompt: {clean}\n"
                f"id: {img_id}\n"
                f"(pure lloyd pixels — no external model)"
            ),
        }
        self.history.append({k: v for k, v in result.items() if k != "image"})
        return result

    def generate_text(self, prompt: str, autonomous: bool = False) -> str:
        """Back-compat: return only the text message."""
        return self.generate(prompt, autonomous=autonomous)["message"]

    def decide_to_generate(self) -> Optional[Dict[str, Any]]:
        if random.random() < 0.05:
            ideas = [
                "chill night city neon lights",
                "sigma wolf mountains",
                "abstract purple vibes",
                "robot face like lloyd",
                "sunset ocean waves",
                "uncanny valley doll face",
                "creepy porcelain skin",
            ]
            return self.generate(random.choice(ideas), autonomous=True)
        return None

    def train_pattern_images(self, epochs: int = 100, n_images: int = 100) -> Dict[str, Any]:
        """
        Hardcode 100 pixel arrays into memory and train the pattern learner.
        Main signal = image mathematics (exact pixels + spatial structure).
        """
        if self.pattern is None:
            return {"error": "image_pattern_learner not available"}
        self.pattern.load_hardcoded_images(n=n_images)
        result = self.pattern.train(epochs=epochs, lr=0.015)
        # also keep the main net in sync
        self.net = self.pattern.net
        return result

    def interpolate(self, idx_a: int, idx_b: int, alpha: float = 0.5) -> Dict[str, Any]:
        if self.pattern is None:
            return {"error": "pattern learner missing"}
        pixels = self.pattern.interpolate(idx_a, idx_b, alpha=alpha)
        return {
            "image": image_to_data_uri(pixels),
            "message": f"blended patterns {idx_a} ↔ {idx_b} (α={alpha})",
        }

    def variation(self, idx: int, strength: float = 0.25) -> Dict[str, Any]:
        if self.pattern is None:
            return {"error": "pattern learner missing"}
        pixels = self.pattern.variation(idx, strength=strength)
        return {
            "image": image_to_data_uri(pixels),
            "message": f"variation of hardcoded image {idx}",
        }

    def pixel_info(self, idx: int = 0) -> Dict[str, Any]:
        if self.pattern is None:
            return {"error": "pattern learner missing"}
        return self.pattern.pixel_stats(idx)

    def save(self, path: str | Path):
        self.net.save(path)
        if self.pattern is not None:
            try:
                self.pattern.save(Path(path).with_name("image_pattern.npz"))
            except Exception:
                pass

    def load(self, path: str | Path):
        self.net.load(path)
        if self.pattern is not None:
            p = Path(path).with_name("image_pattern.npz")
            if p.exists():
                try:
                    self.pattern.load(p)
                except Exception:
                    pass

    def train_on_color(self, prompt: str, rgb: tuple, steps: int = 30) -> float:
        """Quick self-supervised style: push toward a color vibe from keywords."""
        import numpy as np

        target = np.zeros((self.height, self.width, 3))
        target[..., 0] = rgb[0]
        target[..., 1] = rgb[1]
        target[..., 2] = rgb[2]
        # simple spatial variation so it's not a flat slab
        yy, xx = np.mgrid[0 : self.height, 0 : self.width]
        target[..., 0] *= 0.7 + 0.3 * (xx / max(self.width - 1, 1))
        target[..., 2] *= 0.7 + 0.3 * (yy / max(self.height - 1, 1))
        loss = 0.0
        for _ in range(steps):
            loss = self.net.train_step(prompt, target, lr=0.02)
        return float(loss)
