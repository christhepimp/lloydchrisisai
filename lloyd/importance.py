"""
Lloyd Importance bridge
=======================
Context amplifier holds the dictionary and builds bias for
REAL multi-head attention in TinyTransformer.
No fake attention header.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from lloyd.context_amplifier import (
    amplifier,
    parse_importance,
    DICTIONARY_BOOST_PERCENT,
    MIN_SCORE,
    MAX_SCORE,
)


class ImportanceEngine:
    def __init__(self):
        self.amplifier = amplifier
        self.dictionary = amplifier.dictionary

    def load_dictionary_file(self, path: str) -> int:
        return self.amplifier.load_dictionary_file(path)

    def learn_from_text(self, text: str) -> int:
        n = self.amplifier.learn_from_text(text)
        import re

        for m in re.finditer(
            r"∆\s*([^=∆]+?)\s*=\s*([^∆]+?)\s*∆", text.replace("Δ", "∆")
        ):
            teach_equals(m.group(1).strip(), m.group(2).strip())
        return n

    def score_word(self, word: str) -> Tuple[int, bool]:
        return self.amplifier.score_word(word)

    def status(self) -> str:
        return self.amplifier.status()

    def bias_for_text(self, text: str):
        return self.amplifier.bias_for_text(text)

    def attend(self, text: str):
        """Report dictionary hits that will bias multi-head attention."""
        return self.amplifier.run_report(text)

    def highlight(self, text: str) -> str:
        return self.amplifier.run_report(text)


engine = ImportanceEngine()

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
            engine.highlight(sample),
        ]
    )
