"""
Lloyd Context Amplifier (own program)
=====================================
Holds the category dictionary (words + phrases).
Produces an importance bias injected into REAL multi-head attention
(TinyTransformer) — not a fake header.

Math:
  plain +   CODING | HACKING | SLANG | ATTITUDE
  +$        STRUCTURE | HUMOR | PATTERN (neighbor spill)

DICTIONARY_BOOST_PERCENT = 95  (raised for stronger +7/+10 effect)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

MIN_SCORE = -10
MAX_SCORE = 10
DICTIONARY_BOOST_PERCENT = 95
CONTEXT_RADIUS = 2
CONTEXT_SPILL = 0.40
_LOGIT_SCALE = 6.5

_MARKER_RE = re.compile(
    r"∆\s*<\s*([^∆+\-$]+?)\s*([+-]\d+)\s*(\$?)\s*∆"
    r"|"
    r"∆\s*([^∆+\-$]+?)\s*([+-]\d+)\s*(\$?)\s*∆",
    re.UNICODE,
)


def _clamp(n: int) -> int:
    return max(MIN_SCORE, min(MAX_SCORE, int(n)))


def parse_importance(text: str) -> List[Tuple[str, int, bool]]:
    found: List[Tuple[str, int, bool]] = []
    for m in _MARKER_RE.finditer(text.replace("Δ", "∆")):
        if m.group(1) is not None:
            word, score_s, dollar = m.group(1), m.group(2), m.group(3)
        else:
            word, score_s, dollar = m.group(4), m.group(5), m.group(6)
        word = " ".join(word.strip().lower().split())
        found.append((word, _clamp(int(score_s)), dollar == "$"))
    return found


class Dictionary:
    def __init__(self):
        self.table: Dict[str, Tuple[int, bool]] = {}
        self._load_words()
        self._load_phrases()
        path = Path(__file__).parent / "dictionary" / "special_plus10s.txt"
        if path.exists():
            try:
                self.load_file(str(path))
            except Exception:
                pass

    def _load_words(self):
        try:
            from lloyd.dictionary import build_full_dict as bfd

            for w in bfd.DOLLAR_CATS | bfd.PLAIN_CATS:
                score, use_dollar = bfd.score_and_dollar(w)
                if score != 0:
                    self.table[w] = (_clamp(score), use_dollar)
        except Exception:
            pass

    def _load_phrases(self):
        try:
            from lloyd.dictionary.phrases import PHRASES

            for phrase, (score, dollar) in PHRASES.items():
                key = " ".join(phrase.lower().split())
                self.table[key] = (_clamp(score), dollar)
        except Exception:
            pass

    def load_file(self, path: str) -> int:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        n = 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for word, score, dollar in parse_importance(line):
                self.table[word] = (_clamp(score), dollar)
                n += 1
        return n

    def learn_from_text(self, text: str) -> int:
        n = 0
        for word, score, dollar in parse_importance(text):
            prev = self.table.get(word)
            if prev is None:
                self.table[word] = (_clamp(score), dollar)
            else:
                old_s, old_d = prev
                new_s = _clamp(score)
                if abs(new_s) >= abs(old_s):
                    self.table[word] = (new_s, old_d or dollar)
                else:
                    self.table[word] = (old_s, old_d or dollar)
            n += 1
        return n

    def get(self, key: str) -> Tuple[int, bool]:
        return self.table.get(key.lower().strip(), (0, False))

    def phrase_keys(self) -> List[str]:
        return sorted(
            (k for k in self.table if " " in k),
            key=lambda s: len(s.split()),
            reverse=True,
        )

    def status(self) -> str:
        words = sum(1 for k in self.table if " " not in k)
        phrases = sum(1 for k in self.table if " " in k)
        dollar_n = sum(1 for _, d in self.table.values() if d)
        return (
            f"dict words={words} phrases={phrases} "
            f"$entries={dollar_n} boost={DICTIONARY_BOOST_PERCENT}%"
        )


class ContextAmplifier:
    """Owns dictionary; builds multi-head attention bias."""

    def __init__(self):
        self.dictionary = Dictionary()

    def load_dictionary_file(self, path: str) -> int:
        return self.dictionary.load_file(path)

    def learn_from_text(self, text: str) -> int:
        return self.dictionary.learn_from_text(text)

    def score_word(self, word: str) -> Tuple[int, bool]:
        return self.dictionary.get(word)

    def _match_token_spans(self, tokens: List[str]) -> List[Tuple[int, int, int, bool]]:
        n = len(tokens)
        covered = [False] * n
        spans: List[Tuple[int, int, int, bool]] = []
        lower = [t.lower() for t in tokens]

        for phrase in self.dictionary.phrase_keys():
            parts = phrase.split()
            plen = len(parts)
            if plen == 0 or plen > n:
                continue
            sc, dol = self.dictionary.get(phrase)
            if sc == 0:
                continue
            for i in range(0, n - plen + 1):
                if any(covered[i : i + plen]):
                    continue
                if lower[i : i + plen] == parts:
                    spans.append((i, i + plen, sc, dol))
                    for j in range(i, i + plen):
                        covered[j] = True

        for i, tok in enumerate(lower):
            if covered[i]:
                continue
            sc, dol = self.dictionary.get(tok)
            if sc != 0:
                spans.append((i, i + 1, sc, dol))
                covered[i] = True
        return spans

    def bias_for_text(self, text: str) -> np.ndarray:
        """Char-aligned bias for multi-head attention logits."""
        if not text:
            return np.zeros(0, dtype=np.float64)

        token_matches = list(re.finditer(r"[a-zA-Z0-9']+", text))
        tokens = [m.group(0) for m in token_matches]
        n = len(text)
        raw = np.zeros(n, dtype=np.float64)
        spans = self._match_token_spans(tokens)

        for start_t, end_t, sc, dol in spans:
            intensity = (abs(sc) / float(MAX_SCORE)) * (DICTIONARY_BOOST_PERCENT / 100.0)
            sign = 1.0 if sc >= 0 else -1.0
            strength = sign * intensity * _LOGIT_SCALE
            for ti in range(start_t, end_t):
                m = token_matches[ti]
                raw[m.start() : m.end()] = strength

        out = raw.copy()
        for start_t, end_t, sc, dol in spans:
            if not dol:
                continue
            intensity = (abs(sc) / float(MAX_SCORE)) * (DICTIONARY_BOOST_PERCENT / 100.0)
            sign = 1.0 if sc >= 0 else -1.0
            strength = sign * intensity * _LOGIT_SCALE
            for d in range(1, CONTEXT_RADIUS + 1):
                spill = strength * CONTEXT_SPILL * (1.0 / d)
                for ti in (start_t - d, end_t - 1 + d):
                    if 0 <= ti < len(token_matches):
                        m = token_matches[ti]
                        out[m.start() : m.end()] += spill
        return out

    def run_report(self, text: str) -> str:
        tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())
        spans = self._match_token_spans(tokens)
        if not spans:
            return "no dictionary hits — multi-head runs unboosted"
        parts = []
        for s, e, sc, dol in spans:
            phrase = " ".join(tokens[s:e])
            parts.append(f"{phrase}({sc:+d}{' $' if dol else ''})")
        bias = self.bias_for_text(text)
        peak = float(np.max(np.abs(bias))) if bias.size else 0.0
        return (
            f"amplifier → multi-head bias | boost={DICTIONARY_BOOST_PERCENT}% | "
            f"peak_logit_bias={peak:.2f}\n"
            + ", ".join(parts)
        )

    def status(self) -> str:
        return (
            f"context amplifier → multi-head attention | "
            f"DICTIONARY_BOOST_PERCENT={DICTIONARY_BOOST_PERCENT} | "
            + self.dictionary.status()
        )


amplifier = ContextAmplifier()
