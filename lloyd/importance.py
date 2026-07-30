"""
Lloyd Importance + Attention Header
===================================
1) Attention header runs alone (never reads the dictionary).
2) Dictionary boosts header scores for valued WORDS and PHRASES.
   - plain +   : CODING | HACKING | SLANG | ATTITUDE
   - +$        : STRUCTURE | HUMOR | PATTERN (+ context spread)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    found: List[Tuple[str, int, bool]] = []
    for m in _MARKER_RE.finditer(text.replace("Δ", "∆")):
        if m.group(1) is not None:
            word, score_s, dollar = m.group(1), m.group(2), m.group(3)
        else:
            word, score_s, dollar = m.group(4), m.group(5), m.group(6)
        word = " ".join(word.strip().lower().split())
        found.append((word, _clamp(int(score_s)), dollar == "$"))
    return found


class AttentionHeader:
    """Pure attention. Never consults the dictionary."""

    _SHAPE_BUMP = {
        "what": 0.8, "who": 0.8, "why": 0.8, "how": 0.8, "where": 0.8, "when": 0.8,
        "is": 0.3, "are": 0.3, "was": 0.3, "were": 0.3, "do": 0.3, "does": 0.3,
    }

    def score(self, tokens: List[str]) -> List[float]:
        n = len(tokens)
        if n == 0:
            return []
        out = []
        for i, tok in enumerate(tokens):
            t = tok.lower()
            recency = (i + 1) / n
            length_pulse = 0.4 if len(t) <= 2 else min(1.2, 0.5 + len(t) * 0.06)
            shape = self._SHAPE_BUMP.get(t, 0.0)
            out.append(float(0.5 * recency + 0.35 * length_pulse + shape))
        return out


class ImportanceDictionary:
    """
    Single words + multi-word phrases.
    Only used to boost header scores — header never reads this.
    """

    def __init__(self):
        self.table: Dict[str, Tuple[int, bool]] = {}  # key may contain spaces
        self._load_builtin_categories()
        self._load_phrases()
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

    def _load_phrases(self):
        try:
            from lloyd.dictionary.phrases import PHRASES

            for phrase, (score, dollar) in PHRASES.items():
                key = " ".join(phrase.lower().split())
                self.table[key] = (_clamp(score), dollar)
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
            f"dictionary: {words} words + {phrases} phrases | "
            f"+$ amplifier entries: {dollar_n} | clamp [{MIN_SCORE}, {MAX_SCORE}]"
        )


def _match_spans(
    tokens: List[str], dictionary: ImportanceDictionary
) -> List[Tuple[int, int, int, bool]]:
    """
    Longest-first phrase/word match on token stream.
    Returns list of (start_idx, end_idx_exclusive, score, has_dollar).
    Non-overlapping; longer phrases win.
    """
    n = len(tokens)
    covered = [False] * n
    spans: List[Tuple[int, int, int, bool]] = []

    # phrases first (longest already sorted in phrase_keys)
    lower_tokens = [t.lower() for t in tokens]
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
            if lower_tokens[i : i + plen] == parts:
                spans.append((i, i + plen, sc, dol))
                for j in range(i, i + plen):
                    covered[j] = True

    # single words on remaining tokens
    for i, tok in enumerate(lower_tokens):
        if covered[i]:
            continue
        sc, dol = dictionary.get(tok)
        if sc != 0:
            spans.append((i, i + 1, sc, dol))
            covered[i] = True

    return spans


def apply_dictionary_boost(
    tokens: List[str],
    header_weights: List[float],
    dictionary: ImportanceDictionary,
) -> List[float]:
    """
    Header weights in → boost only dictionary hits (words + phrases) → out.
    $ spreads boost to neighboring tokens outside the matched span.
    """
    n = len(tokens)
    assert len(header_weights) == n
    out = [float(w) for w in header_weights]
    direct = [0.0] * n
    dollar_center = [False] * n

    for start, end, sc, dol in _match_spans(tokens, dictionary):
        for i in range(start, end):
            direct[i] += float(sc)
            out[i] += float(sc)
            if dol:
                dollar_center[i] = True

    for i in range(n):
        if not dollar_center[i] or direct[i] == 0:
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


class ImportanceEngine:
    def __init__(self):
        self.header = AttentionHeader()
        self.dictionary = ImportanceDictionary()

    def load_dictionary_file(self, path: str) -> int:
        return self.dictionary.load_dictionary_file(path)

    def learn_from_text(self, text: str) -> int:
        return self.dictionary.learn_from_text(text)

    def score_word(self, word: str) -> Tuple[int, bool]:
        return self.dictionary.get(word)

    def status(self) -> str:
        return "attention header: independent | " + self.dictionary.status()

    def attend(self, text: str) -> List[Tuple[str, float, float, float]]:
        tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())
        header_w = self.header.score(tokens)
        boosted = apply_dictionary_boost(tokens, header_w, self.dictionary)

        # dict score per token (from spans)
        dict_scores = [0.0] * len(tokens)
        for start, end, sc, _dol in _match_spans(tokens, self.dictionary):
            for i in range(start, end):
                dict_scores[i] = float(sc)

        rows = []
        for i, tok in enumerate(tokens):
            rows.append((tok, header_w[i], boosted[i], dict_scores[i]))
        return rows

    def attention_header(self, text: str) -> List[Tuple[str, float]]:
        return [(t, b) for t, _, b, _ in self.attend(text)]

    def header_only(self, text: str) -> List[Tuple[str, float]]:
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
    sample = "write code first then debug the code because the pattern repeats"
    lines = [
        f"2 + 3 equals {apply_plus(2, 3)}",
        engine.status(),
        "header only: " + " ".join(f"{t}={w:.1f}" for t, w in engine.header_only(sample)),
        "after dict:  " + engine.highlight(sample),
    ]
    return "\n".join(lines)
