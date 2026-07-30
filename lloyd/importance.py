"""
Lloyd Importance + Attention Header
===================================
Hard-coded guide while the neural header is still learning.

Marker math:
  ∆word+10∆   → word is important (score clamped [-10, +10])
  ∆word+10$∆  → important + context amplifier (boost nearby words)

Attention header:
  Runs on its own from word scores.
  Context amplifier ($) adds a boost to surrounding tokens — not a replacement.

Dictionary categories (see lloyd/dictionary/):
  STRUCTURE | HUMOR | PATTERN  →  markers with $
  CODING | HACKING | SLANG | ATTITUDE  →  plain +
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── marker patterns ──────────────────────────────────────────────
# ∆word+10∆  or  ∆word+10$∆  or  ∆word-3$∆
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
# How far $ spreads (tokens to each side)
CONTEXT_RADIUS = 2
# Fraction of center score given to each neighbor when $ is set
CONTEXT_BOOST = 0.35


def _clamp(n: int) -> int:
    return max(MIN_SCORE, min(MAX_SCORE, int(n)))


def parse_importance(text: str) -> List[Tuple[str, int, bool]]:
    """
    Parse markers from text.
    Returns list of (word, score, has_dollar).
    Accepts both ∆word+10∆ and ∆<word+10∆ forms.
    """
    found: List[Tuple[str, int, bool]] = []
    for m in _MARKER_RE.finditer(text.replace("Δ", "∆")):
        if m.group(1) is not None:
            word, score_s, dollar = m.group(1), m.group(2), m.group(3)
        else:
            word, score_s, dollar = m.group(4), m.group(5), m.group(6)
        word = word.strip().lower()
        score = _clamp(int(score_s))
        found.append((word, score, dollar == "$"))
    return found


class ImportanceEngine:
    """
    Word → score table + attention header scoring with optional $ boost.
    """

    def __init__(self):
        # word -> (score, has_dollar)
        self.table: Dict[str, Tuple[int, bool]] = {}
        self._load_builtin_categories()
        # try file override
        default = Path(__file__).parent / "dictionary" / "special_plus10s.txt"
        if default.exists():
            try:
                self.load_dictionary_file(str(default))
            except Exception:
                pass

    def _load_builtin_categories(self):
        """Seed from build_full_dict category sets if import works."""
        try:
            from lloyd.dictionary import build_full_dict as bfd

            all_words = bfd.DOLLAR_CATS | bfd.PLAIN_CATS
            for w in all_words:
                score, use_dollar = bfd.score_and_dollar(w)
                if score != 0:
                    self.table[w] = (_clamp(score), use_dollar)
        except Exception:
            pass

    def load_dictionary_file(self, path: str) -> int:
        """Load ∆word+N∆ / ∆word+N$∆ lines from special_plus10s.txt."""
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
        """Learn markers embedded in free text / lessons."""
        n = 0
        for word, score, dollar in parse_importance(text):
            prev = self.table.get(word)
            if prev is None:
                self.table[word] = (_clamp(score), dollar)
            else:
                # keep stronger abs score; $ sticks if either has it
                old_s, old_d = prev
                new_s = _clamp(score)
                if abs(new_s) >= abs(old_s):
                    self.table[word] = (new_s, old_d or dollar)
                else:
                    self.table[word] = (old_s, old_d or dollar)
            n += 1
        # equals inside ∆a=b∆
        for m in _EQUALS_RE.finditer(text.replace("Δ", "∆")):
            teach_equals(m.group(1).strip(), m.group(2).strip())
        return n

    def score_word(self, word: str) -> Tuple[int, bool]:
        w = word.lower().strip()
        return self.table.get(w, (0, False))

    def attention_header(self, text: str) -> List[Tuple[str, float]]:
        """
        Attention header — works on its own from dictionary scores.
        Then context amplifier ($) boosts neighbors of $ words.
        Returns list of (token, attention_weight).
        """
        tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())
        if not tokens:
            return []

        n = len(tokens)
        # Base attention from dictionary (header alone)
        base = [0.0] * n
        dollar_flags = [False] * n
        for i, tok in enumerate(tokens):
            sc, dol = self.score_word(tok)
            base[i] = float(sc)
            dollar_flags[i] = dol

        # Context amplifier boost — only from $ centers
        boosted = base[:]
        for i, dol in enumerate(dollar_flags):
            if not dol or base[i] == 0:
                continue
            spread = abs(base[i]) * CONTEXT_BOOST
            for d in range(1, CONTEXT_RADIUS + 1):
                if i - d >= 0:
                    # neighbors inherit a fraction; sign follows center
                    boosted[i - d] += spread * (1.0 / d) * (1 if base[i] > 0 else -1)
                if i + d < n:
                    boosted[i + d] += spread * (1.0 / d) * (1 if base[i] > 0 else -1)

        # clamp display weights into a soft range
        out: List[Tuple[str, float]] = []
        for tok, w in zip(tokens, boosted):
            w = max(float(MIN_SCORE), min(float(MAX_SCORE), w))
            out.append((tok, w))
        return out

    def highlight(self, text: str) -> str:
        """Human-readable attention map."""
        att = self.attention_header(text)
        if not att:
            return "(empty)"
        parts = []
        for tok, w in att:
            if abs(w) < 0.5:
                parts.append(tok)
            else:
                parts.append(f"{tok}[{w:+.1f}]")
        return " ".join(parts)

    def status(self) -> str:
        dollar_n = sum(1 for _, d in self.table.values() if d)
        plain_n = len(self.table) - dollar_n
        return (
            f"importance lexicon: {len(self.table)} words | "
            f"plain +: {plain_n} | +$ amplifier: {dollar_n} | "
            f"clamp [{MIN_SCORE}, {MAX_SCORE}]"
        )


# Global engine (header guide)
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
    # ∆a=b∆
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


# ── basic numeric ops (1–10 world + general ints) ─────────────────
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
    lines = [
        f"2 + 3 equals {apply_plus(2, 3)}",
        f"7 - 4 equals {apply_minus(7, 4)}",
        f"5 equals 5? {apply_equals_numeric(5, 5)}",
        compare_numbers(9, 3),
        engine.status(),
        "attention demo: " + engine.highlight(
            "the dog barked because the code was funny"
        ),
    ]
    return "\n".join(lines)
