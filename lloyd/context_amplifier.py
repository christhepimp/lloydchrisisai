"""
Lloyd Context Amplifier (own program)
=====================================
Holds the category dictionary (words + phrases).
Communicates with the attention header by reading the header's scores,
then boosting words/phrases the header already put value on when they
appear in the dictionary.

This is NOT a digit. "$" on a dictionary entry only means "also boost
neighbors." The amplifier itself is this module.

Math on dictionary entries:
  plain +   CODING | HACKING | SLANG | ATTITUDE
  +$        STRUCTURE | HUMOR | PATTERN  (neighbor spill on)

Boost strength (easy to change later):
  DICTIONARY_BOOST_PERCENT = 68  → +68% on header score for full +10 hits
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lloyd.attention_header import AttentionHeader, header as default_header

MIN_SCORE = -10
MAX_SCORE = 10

# TUNABLE — main boost the amplifier applies to header scores
DICTIONARY_BOOST_PERCENT = 68

# Neighbor spill when dictionary entry uses $ (context spread)
CONTEXT_RADIUS = 2
CONTEXT_SPILL = 0.35

_MARKER_RE = re.compile(
    r"∆\s*<\s*([^∆+\-$]+?)\s*([+-]\d+)\s*(\$?)\s*∆"
    r"|"
    r"∆\s*([^∆+\-$]+?)\s*([+-]\d+)\s*(\$?)\s*∆",
    re.UNICODE,
)
_EQUALS_RE = re.compile(
    r"∆\s*([^=∆]+?)\s*=\s*([^∆]+?)\s*∆",
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


def _boost_factor(dict_score: int) -> float:
    if dict_score == 0:
        return 1.0
    intensity = abs(dict_score) / float(MAX_SCORE)
    delta = (DICTIONARY_BOOST_PERCENT / 100.0) * intensity
    if dict_score > 0:
        return 1.0 + delta
    return max(0.0, 1.0 - delta)


class Dictionary:
    """Category dictionary owned by the context amplifier."""

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


def _match_spans(
    tokens: List[str], dictionary: Dictionary
) -> List[Tuple[int, int, int, bool]]:
    n = len(tokens)
    covered = [False] * n
    spans: List[Tuple[int, int, int, bool]] = []
    lower = [t.lower() for t in tokens]

    for phrase in dictionary.phrase_keys():
        parts = phrase.split()
        plen = len(parts)
        if plen == 0 or plen > n:
            continue
        sc, dol = dictionary.get(phrase)
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
        sc, dol = dictionary.get(tok)
        if sc != 0:
            spans.append((i, i + 1, sc, dol))
            covered[i] = True
    return spans


class ContextAmplifier:
    """
    Own program:
      - holds the dictionary
      - reads attention-header scores
      - boosts scores for dictionary hits
      - optional $ neighbor spill
    """

    def __init__(self, attn_header: Optional[AttentionHeader] = None):
        self.dictionary = Dictionary()
        self.header = attn_header or default_header

    def load_dictionary_file(self, path: str) -> int:
        return self.dictionary.load_file(path)

    def learn_from_text(self, text: str) -> int:
        return self.dictionary.learn_from_text(text)

    def score_word(self, word: str) -> Tuple[int, bool]:
        return self.dictionary.get(word)

    def boost(
        self,
        tokens: List[str],
        header_weights: List[float],
    ) -> List[float]:
        """
        Communicate with header output: take header weights, return boosted.
        Only dictionary-valued words/phrases get the % boost.
        """
        n = len(tokens)
        assert len(header_weights) == n
        out = [float(w) for w in header_weights]
        deltas = [0.0] * n
        dollar_center = [False] * n

        for start, end, sc, dol in _match_spans(tokens, self.dictionary):
            factor = _boost_factor(sc)
            for i in range(start, end):
                old = out[i]
                new = old * factor
                deltas[i] += new - old
                out[i] = new
                if dol:
                    dollar_center[i] = True

        for i in range(n):
            if not dollar_center[i] or deltas[i] == 0:
                continue
            for d in range(1, CONTEXT_RADIUS + 1):
                spill = deltas[i] * CONTEXT_SPILL * (1.0 / d)
                if i - d >= 0:
                    out[i - d] += spill
                if i + d < n:
                    out[i + d] += spill
        return out

    def run(self, text: str) -> List[Tuple[str, float, float, float]]:
        """
        Full pipeline this program owns the second half of:
          1) ask header to score (header stays independent)
          2) amplifier boosts using dictionary
        Returns (token, header_score, boosted_score, dict_value).
        """
        tokens = self.header.tokenize(text)
        header_w = self.header.score_tokens(tokens)
        boosted = self.boost(tokens, header_w)

        dict_scores = [0.0] * len(tokens)
        for start, end, sc, _dol in _match_spans(tokens, self.dictionary):
            for i in range(start, end):
                dict_scores[i] = float(sc)

        return [
            (tok, header_w[i], boosted[i], dict_scores[i])
            for i, tok in enumerate(tokens)
        ]

    def status(self) -> str:
        return (
            f"context amplifier online | "
            f"DICTIONARY_BOOST_PERCENT={DICTIONARY_BOOST_PERCENT} | "
            + self.dictionary.status()
        )

    def highlight(self, text: str) -> str:
        rows = self.run(text)
        if not rows:
            return "(empty)"
        parts = []
        for tok, h, b, d in rows:
            if abs(b - h) < 0.05 and abs(h) < 0.8:
                parts.append(tok)
            else:
                parts.append(f"{tok}[h={h:.1f}→{b:.1f}]")
        return " ".join(parts)


# Global context amplifier instance (holds the dictionary)
amplifier = ContextAmplifier()
