"""
Lloyd's Pure-Scratch Vector Memory
==================================
Simple vector memory implemented from scratch (no external vector DB).
Portable via save() / load().
"""

import numpy as np
from typing import List, Tuple, Optional
import json
import os


class VectorMemory:
    def __init__(self, dim: int = 32, max_items: int = 1000):
        self.dim = dim
        self.max_items = max_items
        self.vectors: List[np.ndarray] = []
        self.texts: List[str] = []
        self.metadata: List[dict] = []

    def _embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim)
        for i, char in enumerate(text.lower()[:self.dim * 4]):
            vec[i % self.dim] += (ord(char) % 97) / 26.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def add(self, text: str, meta: Optional[dict] = None):
        if len(self.vectors) >= self.max_items:
            self.vectors.pop(0)
            self.texts.pop(0)
            self.metadata.pop(0)

        self.vectors.append(self._embed(text))
        self.texts.append(text)
        self.metadata.append(meta or {})

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if not self.vectors:
            return []

        q = self._embed(query)
        scores = [float(np.dot(q, v)) for v in self.vectors]
        ranked = sorted(zip(self.texts, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def save(self, path: str = "lloyd_memory.json"):
        data = {
            "dim": self.dim,
            "texts": self.texts,
            "metadata": self.metadata,
            "vectors": [v.tolist() for v in self.vectors],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load(self, path: str = "lloyd_memory.json"):
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.dim = data.get("dim", self.dim)
        self.texts = data.get("texts", [])
        self.metadata = data.get("metadata", [])
        self.vectors = [np.array(v) for v in data.get("vectors", [])]
