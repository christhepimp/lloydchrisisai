"""
Lloyd Importance + Attention Header
===================================
TWO SEPARATE SYSTEMS:

1) Attention header  — runs on its own. Never reads the dictionary.
2) Dictionary boost  — after the header scores tokens, words that have
   values in the dictionary get a boost (and $ spreads that boost nearby).

Marker math (dictionary only):
  ∆word+10∆   → boost this word
  ∆word+10$∆  → boost this word + context amplifier on neighbors
  clamp       → never over +10 or under -10

Categories (see lloyd/dictionary/):
  STRUCTURE | HUMOR | PATTERN           →  +$
  CODING | HACKING | SLANG | ATTITUDE   →  plain +
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── marker patterns (dictionary file / lesson text only) ─────────
_MARKER_RE = re.compile(
    r"∆\s*<\s*([^∆+\-$\s]+)\s*([+-]\d+)\s*(\$?)\s*∆"
    r"|"
    r"∆\s*([^∆+\-$\s]+)\s*([+-]\d+)\s*(\$?)\s*∆",
    re.UNICODE,
)
_EQUALS_RE = re.compile(
    r"∆\s*([^=∆]+?)\s*=\s*([^∆]+?)\s*∆",
    re.UNICODE,
)
_EQUALS_STATEMENT = re.compile(
    r"^\s*(.+?)\s+equals\s+(.+?)\s*$",
    re.IGNORECASE,
)

MIN_SCORE = -10
MAX_SCORE = 10
CONTEXT_RADIUS = 2
CONTEXT_BOOST = 0.35


def _clamp(n: int) -> int:
    return max(MIN_SCORE, min(MAX_SCORE, int(n)))


def parse_importance(text: str) -> List[Tuple[str, int, bool]]:
    """Parse dictionary markers from text. Returns (word, score, has_dollar)."""
    found: List[Tuple[str, int, bool]] = []
    for m in _MARKER_RE.finditer(text.replace("Δ", "∆")):
        if m.group(1) is not None:
            word, score_s, dollar = m.group(1), m.group(2), m.group(3)
        else:
            word, score_s, dollar = m.group(4), m.group(5), m.group(6)
        word = word.strip().lower()
        found.append((word, _clamp(int(score_s)), dollar == "$"))
    return found


# =====================================================================
# 1) ATTENTION HEADER — independent. Does NOT touch the dictionary.
# =====================================================================
class AttentionHeader:
    """
    Pure attention over tokens. No dictionary lookups.

    Simple original heuristic while the neural header is still learning:
      - later tokens get a mild recency weight
      - content-ish tokens (len > 2) get a base pulse
      - question words / verbs get a small structural bump from shape only
        (not from any external lexicon file)
    """

    # tiny built-in shape cues (NOT the category dictionary)
    _SHAPE_BUMP = {
        "what": 0.8, "who": 0.8, "why": 0.8, "how": 0.8, "where": 0.8, "when": 0.8,
        "is": 0.3, "are": 0.3, "was": 0.3, "were": 0.3, "do": 0.3, "does": 0.3,
    }

    def score(self, tokens: List[str]) -> List[float]:
        """Return one attention weight per token. Dictionary is never consulted."""
        n = len(tokens)
        if n == 0:
            return []
        out = []
        for i, tok in enumerate(tokens):
            t = tok.lower()
            # recency: 0..1 across the sequence
            recency = (i + 1) / n
            # length pulse: short function-looking vs longer content
            length_pulse = 0.4 if len(t) <= 2 else min(1.2, 0.5 + len(t) * 0.06)
            shape = self._SHAPE_BUMP.get(t, 0.0)
            w = 0.5 * recency + 0.35 * length_pulse + shape
            out.append(float(w))
        return out


# =====================================================================
# 2) DICTIONARY — only boosts header scores for valued words
# =====================================================================
class ImportanceDictionary:
    """Word → (score, has_dollar). Used only as a boost layer."""

    def __init__(self):
        self.table: Dict[str, Tuple[int, bool]] = {}
        self._load_builtin_categories()
        default = Path(__file__).parent / "dictionary" / "special_plus10s.txt"
        if default.exists():
            try:
                self.load_dictionary_file(str(default))
            except Exception:
                pass

    def _load_builtin_categories(self):
        try:
            from lloyd.dictionary import build_full_dict as bfd

            for w in bfd.DOLLAR_CATS | bfd.PLAIN_CATS:
                score, use_dollar = bfd.score_and_dollar(w)
                if score != 0:
                    self.table[w] = (_clamp(score), use_dollar)
        except Exception:
            pass

    def load_dictionary_file(self, path: str) -> int:
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
        for m in _EQUALS_RE.finditer(text.replace("Δ", "∆")):
            teach_equals(m.group(1).strip(), m.group(2).strip())
        return n

    def get(self, word: str) -> Tuple[int, bool]:
        return self.table.get(word.lower().strip(), (0, False))

    def status(self) -> str:
        dollar_n = sum(1 for _, d in self.table.values() if d)
        plain_n = len(self.table) - dollar_n
        return (
            f"dictionary: {len(self.table)} valued words | "
            f"plain +: {plain_n} | +$ amplifier: {dollar_n} | "
            f"clamp [{MIN_SCORE}, {MAX_SCORE}]"
        )


def apply_dictionary_boost(
    tokens: List[str],
    header_weights: List[float],
    dictionary: ImportanceDictionary,
) -> List[float]:
    """
    Dictionary boost layer.
    Header weights come in untouched from AttentionHeader.
    Only tokens present in the dictionary receive an additive boost.
    $ markers also spread a fraction of their boost to neighbors.
    """
    n = len(tokens)
    assert len(header_weights) == n
    out = [float(w) for w in header_weights]

    # direct boosts from dictionary values
    direct = [0.0] * n
    dollar_flags = [False] * n
    for i, tok in enumerate(tokens):
        sc, dol = dictionary.get(tok)
        if sc != 0:
            direct[i] = float(sc)
            dollar_flags[i] = dol
            out[i] += float(sc)

    # context amplifier: $ spreads boost to surrounding words
    for i, dol in enumerate(dollar_flags):
        if not dol or direct[i] == 0:
            continue
        spread = abs(direct[i]) * CONTEXT_BOOST
        sign = 1.0 if direct[i] > 0 else -1.0
        for d in range(1, CONTEXT_RADIUS + 1):
            add = spread * (1.0 / d) * sign
            if i - d >= 0:
                out[i - d] += add
            if i + d < n:
                out[i + d] += add

    return out


# =====================================================================
# Engine — wires header then dictionary boost (header never sees dict)
# =====================================================================
class ImportanceEngine:
    def __init__(self):
        self.header = AttentionHeader()
        self.dictionary = ImportanceDictionary()

    # --- dictionary API (used by agent / training) ---
    def load_dictionary_file(self, path: str) -> int:
        return self.dictionary.load_dictionary_file(path)

    def learn_from_text(self, text: str) -> int:
        return self.dictionary.learn_from_text(text)

    def score_word(self, word: str) -> Tuple[int, bool]:
        """Dictionary value only (not header attention)."""
        return self.dictionary.get(word)

    def status(self) -> str:
        return (
            "attention header: independent (no dictionary) | "
            + self.dictionary.status()
        )

    # --- full pipeline ---
    def attend(self, text: str) -> List[Tuple[str, float, float, float]]:
        """
        Returns list of (token, header_weight, dict_boosted_weight, dict_score).
        Header is computed first with zero knowledge of the dictionary.
        """
        tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())
        header_w = self.header.score(tokens)
        boosted = apply_dictionary_boost(tokens, header_w, self.dictionary)
        rows = []
        for i, tok in enumerate(tokens):
            sc, _ = self.dictionary.get(tok)
            rows.append((tok, header_w[i], boosted[i], float(sc)))
        return rows

    def attention_header(self, text: str) -> List[Tuple[str, float]]:
        """Final weights after dictionary boost (for callers that want one list)."""
        return [(t, b) for t, _, b, _ in self.attend(text)]

    def header_only(self, text: str) -> List[Tuple[str, float]]:
        """Pure header — dictionary never involved."""
        tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())
        weights = self.header.score(tokens)
        return list(zip(tokens, weights))

    def highlight(self, text: str) -> str:
        rows = self.attend(text)
        if not rows:
            return "(empty)"
        parts = []
        for tok, h, b, d in rows:
            if abs(b - h) < 0.05 and abs(h) < 0.8:
                parts.append(tok)
            else:
                parts.append(f"{tok}[h={h:.1f}→{b:.1f}]")
        return " ".join(parts)


# Global engine
engine = ImportanceEngine()


# ── equals graph ─────────────────────────────────────────────────
_EQUALS: Dict[str, set] = {}


def teach_equals(a: str, b: str):
    a, b = a.strip().lower(), b.strip().lower()
    if not a or not b:
        return
    _EQUALS.setdefault(a, set()).add(b)
    _EQUALS.setdefault(b, set()).add(a)


def equals(a: str, b: str) -> str:
    a, b = a.strip().lower(), b.strip().lower()
    if a == b:
        return "yes"
    if b in _EQUALS.get(a, set()):
        return "yes"
    return "no"


def what_equals(thing: str) -> List[str]:
    return sorted(_EQUALS.get(thing.strip().lower(), set()))


def parse_equals_statement(text: str) -> Optional[Tuple[str, str]]:
    text = text.strip()
    m = _EQUALS_RE.search(text.replace("Δ", "∆"))
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = _EQUALS_STATEMENT.match(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    if "=" in text and "∆" not in text and len(text) < 80:
        left, _, right = text.partition("=")
        left, right = left.strip(), right.strip()
        if left and right and " " not in left and " " not in right:
            return left, right
    return None


def apply_plus(a: int, b: int) -> int:
    return a + b


def apply_minus(a: int, b: int) -> int:
    return a - b


def apply_equals_numeric(a: int, b: int) -> str:
    return "yes" if a == b else "no"


def compare_numbers(a: int, b: int) -> str:
    if a > b:
        return f"{a} is greater than {b}"
    if a < b:
        return f"{a} is less than {b}"
    return f"{a} equals {b}"


def demo_basic_math() -> str:
    sample = "the code was funny because the pattern repeated"
    lines = [
        f"2 + 3 equals {apply_plus(2, 3)}",
        f"7 - 4 equals {apply_minus(7, 4)}",
        f"5 equals 5? {apply_equals_numeric(5, 5)}",
        compare_numbers(9, 3),
        engine.status(),
        "header only:  " + " ".join(f"{t}={w:.1f}" for t, w in engine.header_only(sample)),
        "after dict:   " + engine.highlight(sample),
    ]
    return "\n".join(lines)
