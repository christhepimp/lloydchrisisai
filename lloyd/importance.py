"""
Lloyd Importance bridge
=======================
Compatibility layer used by agent / training_loop.

Real systems:
  lloyd.attention_header   — scores words alone
  lloyd.context_amplifier  — own program; holds dictionary; boosts header scores

"engine.attend()" = header score → amplifier boost.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from lloyd.attention_header import AttentionHeader, header
from lloyd.context_amplifier import (
    ContextAmplifier,
    amplifier,
    parse_importance,
    DICTIONARY_BOOST_PERCENT,
    MIN_SCORE,
    MAX_SCORE,
)

# Re-export for older imports
__all__ = [
    "engine",
    "parse_importance",
    "teach_equals",
    "equals",
    "what_equals",
    "parse_equals_statement",
    "apply_plus",
    "apply_minus",
    "apply_equals_numeric",
    "compare_numbers",
    "demo_basic_math",
    "DICTIONARY_BOOST_PERCENT",
]


class ImportanceEngine:
    """Thin API: header alone + context amplifier (dictionary owner)."""

    def __init__(self):
        self.header = header
        self.amplifier = amplifier
        # alias so older code reading .dictionary still works conceptually
        self.dictionary = amplifier.dictionary

    def load_dictionary_file(self, path: str) -> int:
        return self.amplifier.load_dictionary_file(path)

    def learn_from_text(self, text: str) -> int:
        n = self.amplifier.learn_from_text(text)
        # equals markers still taught here for training stories
        import re

        for m in re.finditer(
            r"∆\s*([^=∆]+?)\s*=\s*([^∆]+?)\s*∆", text.replace("Δ", "∆")
        ):
            teach_equals(m.group(1).strip(), m.group(2).strip())
        return n

    def score_word(self, word: str) -> Tuple[int, bool]:
        return self.amplifier.score_word(word)

    def status(self) -> str:
        return (
            "attention header: independent | "
            + self.amplifier.status()
        )

    def attend(self, text: str) -> List[Tuple[str, float, float, float]]:
        """header scores → context amplifier boosts."""
        return self.amplifier.run(text)

    def attention_header(self, text: str) -> List[Tuple[str, float]]:
        return [(t, b) for t, _, b, _ in self.attend(text)]

    def header_only(self, text: str) -> List[Tuple[str, float]]:
        return self.header.score_text(text)

    def highlight(self, text: str) -> str:
        return self.amplifier.highlight(text)


engine = ImportanceEngine()


# ── equals + basic math (unchanged teaching helpers) ─────────────
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
    import re

    text = text.strip()
    m = re.search(r"∆\s*([^=∆]+?)\s*=\s*([^∆]+?)\s*∆", text.replace("Δ", "∆"))
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r"^\s*(.+?)\s+equals\s+(.+?)\s*$", text, re.I)
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
    sample = "write code first then debug the code because the pattern repeats"
    return "\n".join(
        [
            f"2 + 3 equals {apply_plus(2, 3)}",
            engine.status(),
            "header only: "
            + " ".join(f"{t}={w:.1f}" for t, w in engine.header_only(sample)),
            "amplifier:   " + engine.highlight(sample),
        ]
    )
