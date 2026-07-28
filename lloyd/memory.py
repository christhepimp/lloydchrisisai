"""
Lloyd's Pure-Scratch Vector Memory
==================================
Simple vector memory implemented from scratch (no external vector DB).
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
        """
        Extremely simple bag-of-characters embedding (pure scratch).
        Later we will replace this with real embeddings from the Transformer.
        """
        vec = np.zeros(self.dim)
        for i, char in enumerate(text.lower()[:self.dim * 4]):
            vec[i % self.dim] += (ord(char) % 97) / 26.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def add(self, text: str, meta: Optional[dict] = None):
        if len(self.vectors) >= self.max_items:
            # Remove oldest
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
            "texts": self.texts,
            "metadata": self.metadata,
            "vectors": [v.tolist() for v in self.vectors],
        }
        with open(path, "w") as f:
            json.dump(data, f)

    def load(self, path: str = "lloyd_memory.json"):
        if not os.path.exists(path):
            return
        with open(path, "r") as f:
            data = json.load(f)
        self.texts = data.get("texts", [])
        self.metadata = data.get("metadata", [])
        self.vectors = [np.array(v) for v in data.get("vectors", [])]
