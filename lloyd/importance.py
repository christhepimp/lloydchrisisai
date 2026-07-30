"""
Lloyd Importance + Basic Math Engine
====================================
Hard-coded understanding of:
  =   "equals" — left side equals right side, no matter what is written
  +   addition / positive importance
  -   subtraction / negative importance
  numbers 1–10 and their order
  importance annotations: ∆word+5∆ or ∆word+5$∆

  $ = CONTEXT AMPLIFIER
      When present, importance spreads to surrounding words in text.

Importance ranking rules (hard-coded, exact):
  • No number  =  0   (baseline / zero)
  • Negative numbers (-) are LESS than 0
  • Positive numbers (+) are HIGHER than both 0 and all negatives

  Order is always:
      +numbers  >  0 (no number)  >  -numbers
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

EQUALS = "="
PLUS = "+"
MINUS = "-"

def apply_plus(a: float, b: float) -> float:
    return a + b

def apply_minus(a: float, b: float) -> float:
    return a - b

def apply_equals_numeric(left, right) -> bool:
    return left == right

_equals_links: Dict[str, Set[str]] = {}

def _norm(s: str) -> str:
    return s.strip().lower()

def teach_equals(left: str, right: str):
    l, r = _norm(left), _norm(right)
    if not l or not r:
        return
    if l not in _equals_links:
        _equals_links[l] = set()
    if r not in _equals_links:
        _equals_links[r] = set()
    _equals_links[l].add(r)
    _equals_links[r].add(l)

def equals(left: str, right: str) -> bool:
    l, r = _norm(left), _norm(right)
    if l == r:
        return True
    return r in _equals_links.get(l, set())

def what_equals(thing: str) -> List[str]:
    return sorted(_equals_links.get(_norm(thing), set()))

def parse_equals_statement(text: str) -> Optional[Tuple[str, str]]:
    m = re.match(r"^\s*(.+?)\s*=\s*(.+?)\s*$", text.strip())
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()

NUMBERS = {
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

def number_value(token: str) -> Optional[int]:
    return NUMBERS.get(token.lower())

def compare_numbers(a: int, b: int) -> str:
    if a > b:
        return f"{a} is greater than {b}"
    if a < b:
        return f"{a} is less than {b}"
    return f"{a} equals {b}"

# ──────────────────────────────────────────────
# Importance: ∆word+N∆  or  ∆word+N$∆
# $ = context amplifier (spread to nearby words)
# ──────────────────────────────────────────────

ANNOTATION_RE = re.compile(r"∆([^∆]+)∆")

def parse_importance(text: str) -> List[Tuple[str, int, bool]]:
    """
    Returns list of (phrase, score, context_spread).
    context_spread True when $ is present (e.g. ∆hungry+8$∆).
    """
    results = []
    for match in ANNOTATION_RE.finditer(text):
        content = match.group(1).strip()
        spread = "$" in content
        content_clean = content.replace("$", "").strip()
        m = re.search(r"([+-]\d+)\s*$", content_clean)
        if m:
            score = int(m.group(1))
            phrase = content_clean[: m.start()].strip().lower()
            phrase = re.sub(r"\s*\+\s*", " ", phrase).strip()
            results.append((phrase, score, spread))
        else:
            phrase = re.sub(r"\s*\+\s*", " ", content_clean).strip().lower()
            results.append((phrase, 0, spread))
    return results

def importance_rank(score: int) -> str:
    if score > 0:
        return f"positive +{score} (higher than zero and all negatives)"
    if score < 0:
        return f"negative {score} (less than zero)"
    return "zero / no number (baseline)"

def compare_importance(score_a: int, score_b: int) -> str:
    def category(s: int) -> int:
        if s > 0: return 2
        if s == 0: return 1
        return 0
    cat_a, cat_b = category(score_a), category(score_b)
    if cat_a > cat_b:
        return f"{score_a} is more important than {score_b}"
    if cat_a < cat_b:
        return f"{score_a} is less important than {score_b}"
    if score_a > score_b:
        return f"{score_a} is more important than {score_b}"
    if score_a < score_b:
        return f"{score_a} is less important than {score_b}"
    return f"{score_a} and {score_b} have equal importance"


class ImportanceEngine:
    def __init__(self):
        self.knowledge: Dict[str, int] = {}
        self.patterns: Dict[str, int] = {}
        # words that should spread importance to neighbors
        self.context_spread: Set[str] = set()

    def learn_from_text(self, text: str):
        items = parse_importance(text)
        for phrase, score, spread in items:
            if phrase not in self.knowledge:
                self.knowledge[phrase] = score
            else:
                old = self.knowledge[phrase]
                if (score > 0 and old <= 0) or (score == 0 and old < 0) or (score > old and (score > 0) == (old > 0)):
                    self.knowledge[phrase] = score
            if spread:
                self.context_spread.add(phrase)
                # also mark individual tokens for single-word entries
                for tok in phrase.split():
                    self.context_spread.add(tok)
            words = phrase.split()
            if len(words) >= 2:
                abstract = f"{words[0]}+{'+'.join(words[1:])}"
                if abstract not in self.patterns or score > self.patterns[abstract]:
                    self.patterns[abstract] = score

    def amplify_context(self, tokens: List[str], window: int = 2) -> Dict[str, int]:
        """
        Context Amplifier:
        For any token marked with $, boost nearby tokens within `window`.
        Returns token -> boosted importance map for this sequence.
        """
        n = len(tokens)
        scores = [self.get_importance(t) for t in tokens]
        boosted = scores[:]
        for i, tok in enumerate(tokens):
            key = tok.lower()
            if key in self.context_spread or self.get_importance(key) >= 10:
                base = max(scores[i], 1)
                for j in range(max(0, i - window), min(n, i + window + 1)):
                    if j == i:
                        continue
                    # neighbor gets a fraction of the spread source importance
                    boost = max(1, base // 2)
                    boosted[j] = max(boosted[j], boost)
        return {tokens[i].lower(): boosted[i] for i in range(n)}

    def get_importance(self, phrase: str) -> int:
        return self.knowledge.get(phrase.lower().strip(), 0)

    def best_completion(self, prefix: str, candidates: List[str]) -> Tuple[str, int]:
        prefix = prefix.lower().strip()
        best = candidates[0] if candidates else ""
        best_score = -9999
        for cand in candidates:
            full = f"{prefix} {cand}".lower()
            score = self.knowledge.get(full, 0)
            abstract_score = self.patterns.get(f"{prefix}+{cand}", -9999)
            score = max(score, abstract_score)
            if score > best_score:
                best_score = score
                best = cand
        return best, best_score

    def explain(self, phrase: str) -> str:
        score = self.get_importance(phrase)
        spread = " $" if phrase.lower() in self.context_spread else ""
        return f"∆{phrase}{score:+d}{spread}∆ → {importance_rank(score)}"

    def load_dictionary_file(self, path: str | Path) -> int:
        """Load a full annotated dictionary file (every line ∆word+N∆ or ∆word+N$∆)."""
        path = Path(path)
        if not path.exists():
            return 0
        text = path.read_text(encoding="utf-8", errors="ignore")
        before = len(self.knowledge)
        self.learn_from_text(text)
        return len(self.knowledge) - before

    def status(self) -> str:
        lines = ["Lloyd importance knowledge ( + > 0 > - | $ = context spread ):"]
        for p, s in sorted(self.knowledge.items(), key=lambda x: -x[1])[:20]:
            mark = "$" if p in self.context_spread else ""
            lines.append(f"  ∆{p}{s:+d}{mark}∆")
        lines.append(f"total words known: {len(self.knowledge)} | context-spread tags: {len(self.context_spread)}")
        if self.patterns:
            lines.append("Abstract patterns:")
            for p, s in list(self.patterns.items())[:8]:
                lines.append(f"  {p} → {s:+d}")
        if _equals_links:
            lines.append("Equals links:")
            for k, vals in list(_equals_links.items())[:10]:
                lines.append(f"  {k} equals {', '.join(sorted(vals))}")
        return "\n".join(lines) if len(lines) > 1 else "no importance knowledge yet"


engine = ImportanceEngine()

def demo_basic_math() -> str:
    checks = []
    checks.append(f"2 + 3 = {apply_plus(2, 3)}  (should be 5)")
    checks.append(f"7 - 4 = {apply_minus(7, 4)}  (should be 3)")
    checks.append(f"5 equals 5 ? {apply_equals_numeric(5, 5)}")
    checks.append(compare_numbers(9, 4))
    checks.append("--- general equals rule ---")
    teach_equals("cat", "animal")
    teach_equals("dog", "animal")
    checks.append(f"cat equals animal ? {equals('cat', 'animal')}")
    checks.append(f"dog equals animal ? {equals('dog', 'animal')}")
    checks.append(f"what equals animal? {what_equals('animal')}")
    checks.append("--- context amplifier demo ---")
    engine.learn_from_text("∆hungry+8$∆ ∆code+10$∆")
    checks.append(f"hungry spread? {'hungry' in engine.context_spread}")
    checks.append(f"code score={engine.get_importance('code')}")
    return "\n".join(checks)
