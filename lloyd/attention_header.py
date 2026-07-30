"""
Lloyd Attention Header
======================
Scores a group of words on its own.
Never reads the dictionary. Never talks to the context amplifier directly.

Other systems (context amplifier) may read these scores and boost them.
"""

from __future__ import annotations

import re
from typing import List, Tuple


class AttentionHeader:
    """
    Pure attention over a token group.
    Puts relative value on words by its own rules only.
    """

    _SHAPE_BUMP = {
        "what": 0.8, "who": 0.8, "why": 0.8, "how": 0.8, "where": 0.8, "when": 0.8,
        "is": 0.3, "are": 0.3, "was": 0.3, "were": 0.3, "do": 0.3, "does": 0.3,
    }

    def tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9']+", text.lower())

    def score_tokens(self, tokens: List[str]) -> List[float]:
        """One score per token. Dictionary is never consulted."""
        n = len(tokens)
        if n == 0:
            return []
        out: List[float] = []
        for i, tok in enumerate(tokens):
            t = tok.lower()
            recency = (i + 1) / n
            length_pulse = 0.4 if len(t) <= 2 else min(1.2, 0.5 + len(t) * 0.06)
            shape = self._SHAPE_BUMP.get(t, 0.0)
            out.append(float(0.5 * recency + 0.35 * length_pulse + shape))
        return out

    def score_text(self, text: str) -> List[Tuple[str, float]]:
        """Return (token, header_score) pairs."""
        tokens = self.tokenize(text)
        weights = self.score_tokens(tokens)
        return list(zip(tokens, weights))


# Default instance the rest of Lloyd can share
header = AttentionHeader()
