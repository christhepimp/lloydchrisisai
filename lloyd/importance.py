"""
Lloyd Importance + Basic Math Engine
====================================
Hard-coded understanding of:
  =   equality
  +   addition / positive importance
  -   subtraction / negative importance
  numbers 1–10 and their order
  importance annotations in the form ∆word+5∆ or ∆word1+word2+15∆

Rules (hard-coded):
  • Any positive importance (+N) is more important than no number
  • Any positive is more important than any negative
  • Higher positive number = more important ( +5 > +3 > +1 )
  • Lower negative = less important ( -1 > -3 > -10 )
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple

# ──────────────────────────────────────────────
# 1. Basic arithmetic symbols (always true)
# ──────────────────────────────────────────────

EQUALS = "="
PLUS = "+"
MINUS = "-"

def apply_equals(left, right) -> bool:
    """Hard-coded meaning of = : both sides must be equal."""
    return left == right

def apply_plus(a: float, b: float) -> float:
    """Hard-coded meaning of + : addition."""
    return a + b

def apply_minus(a: float, b: float) -> float:
    """Hard-coded meaning of - : subtraction."""
    return a - b

# ──────────────────────────────────────────────
# 2. Numbers 1–10 with order
# ──────────────────────────────────────────────

NUMBERS = {
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

def number_value(token: str) -> Optional[int]:
    return NUMBERS.get(token.lower())

def is_greater(a: int, b: int) -> bool:
    return a > b

def is_less(a: int, b: int) -> bool:
    return a < b

def compare_numbers(a: int, b: int) -> str:
    if a > b:
        return f"{a} is greater than {b}"
    if a < b:
        return f"{a} is less than {b}"
    return f"{a} equals {b}"

# ──────────────────────────────────────────────
# 3. Importance system
#    Format required: ∆word+5∆  or  ∆dog+eats+20∆
# ──────────────────────────────────────────────

# Matches ∆...∆  (non-greedy inside)
ANNOTATION_RE = re.compile(r"∆([^∆]+)∆")

def parse_importance(text: str) -> List[Tuple[str, int]]:
    """
    Extract all ∆content±N∆ annotations.
    Returns list of (phrase, importance_score).
    Score can be positive or negative.
    """
    results = []
    for match in ANNOTATION_RE.finditer(text):
        content = match.group(1).strip()
        # Look for trailing +N or -N
        m = re.search(r"([+-]\d+)\s*$", content)
        if m:
            score = int(m.group(1))
            phrase = content[: m.start()].strip().lower()
            # clean extra + signs that were separators
            phrase = re.sub(r"\s*\+\s*", " ", phrase).strip()
            results.append((phrase, score))
        else:
            # no explicit number → treat as 0 (baseline)
            phrase = re.sub(r"\s*\+\s*", " ", content).strip().lower()
            results.append((phrase, 0))
    return results

def importance_rank(score: int) -> str:
    """Human-readable rank description."""
    if score > 0:
        return f"positive importance +{score}"
    if score < 0:
        return f"negative importance {score}"
    return "no importance number (baseline)"

def compare_importance(score_a: int, score_b: int) -> str:
    """
    Hard-coded comparison rules:
      any +  >  no number  >  any -
      within positives: higher number wins
      within negatives: closer to zero wins
    """
    def category(s: int) -> int:
        if s > 0:
            return 2
        if s == 0:
            return 1
        return 0  # negative

    cat_a, cat_b = category(score_a), category(score_b)
    if cat_a > cat_b:
        return f"{score_a} is more important than {score_b}"
    if cat_a < cat_b:
        return f"{score_a} is less important than {score_b}"

    # same category
    if score_a > score_b:
        return f"{score_a} is more important than {score_b}"
    if score_a < score_b:
        return f"{score_a} is less important than {score_b}"
    return f"{score_a} and {score_b} have equal importance"

# ──────────────────────────────────────────────
# 4. Simple pattern store + fill-in reasoning
# ──────────────────────────────────────────────

class ImportanceEngine:
    def __init__(self):
        # phrase → best importance score seen
        self.knowledge: Dict[str, int] = {}
        # abstract patterns we have extracted, e.g. "animal action" → score
        self.patterns: Dict[str, int] = {}

    def learn_from_text(self, text: str):
        """Ingest a piece of text that contains ∆...∆ annotations."""
        items = parse_importance(text)
        for phrase, score in items:
            if phrase not in self.knowledge or abs(score) > abs(self.knowledge[phrase]):
                self.knowledge[phrase] = score

            # very light abstract pattern extraction
            words = phrase.split()
            if len(words) >= 2:
                # treat first word as category-ish, rest as action-ish
                abstract = f"{words[0]}+{'+'.join(words[1:])}"
                if abstract not in self.patterns or score > self.patterns[abstract]:
                    self.patterns[abstract] = score

    def get_importance(self, phrase: str) -> int:
        phrase = phrase.lower().strip()
        return self.knowledge.get(phrase, 0)

    def best_completion(self, prefix: str, candidates: List[str]) -> Tuple[str, int]:
        """
        Given a starting word/phrase and a list of possible continuations,
        return the candidate that forms the highest-importance combination
        we know about.
        """
        prefix = prefix.lower().strip()
        best = candidates[0] if candidates else ""
        best_score = -999

        for cand in candidates:
            full = f"{prefix} {cand}".lower()
            score = self.knowledge.get(full, 0)
            # also try the abstract form
            abstract_score = self.patterns.get(f"{prefix}+{cand}", -999)
            score = max(score, abstract_score)
            if score > best_score:
                best_score = score
                best = cand
        return best, best_score

    def explain(self, phrase: str) -> str:
        score = self.get_importance(phrase)
        return f"∆{phrase}{score:+d}∆ → {importance_rank(score)}"

    def status(self) -> str:
        lines = ["Lloyd importance knowledge:"]
        for p, s in sorted(self.knowledge.items(), key=lambda x: -x[1])[:15]:
            lines.append(f"  ∆{p}{s:+d}∆")
        if self.patterns:
            lines.append("Abstract patterns:")
            for p, s in list(self.patterns.items())[:8]:
                lines.append(f"  {p} → {s:+d}")
        return "\n".join(lines) if len(lines) > 1 else "no importance knowledge yet"


# Global engine instance that Lloyd will use
engine = ImportanceEngine()

def demo_basic_math() -> str:
    """Quick self-test of the hard-coded symbols and numbers."""
    checks = []
    checks.append(f"2 + 3 = {apply_plus(2, 3)}  (should be 5)")
    checks.append(f"7 - 4 = {apply_minus(7, 4)}  (should be 3)")
    checks.append(f"5 = 5 ? {apply_equals(5, 5)}")
    checks.append(compare_numbers(9, 4))
    checks.append(compare_numbers(2, 8))
    checks.append(compare_importance(5, 2))
    checks.append(compare_importance(3, 0))
    checks.append(compare_importance(0, -4))
    checks.append(compare_importance(-1, -5))
    return "\n".join(checks)
