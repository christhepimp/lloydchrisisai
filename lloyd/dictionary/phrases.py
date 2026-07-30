"""
Lloyd dictionary phrases & short sentences
==========================================
Multi-word entries that fit the same categories and math as single words.

  STRUCTURE | HUMOR | PATTERN  →  score with $ (context amplifier)
  CODING | HACKING | SLANG | ATTITUDE  →  plain +

Scores clamped to [-10, +10].
Matched longest-first against the attention header token stream, then boost applied.
"""

from __future__ import annotations

# phrase -> (score, use_dollar)
# use_dollar True  => +$ math (STRUCTURE / HUMOR / PATTERN style)
# use_dollar False => plain + (CODING / HACKING / SLANG / ATTITUDE)

PHRASES: dict[str, tuple[int, bool]] = {}


def _add(phrases: list[str], score: int, dollar: bool):
    for p in phrases:
        key = " ".join(p.lower().split())
        if not key:
            continue
        sc = max(-10, min(10, score))
        prev = PHRASES.get(key)
        if prev is None or abs(sc) >= abs(prev[0]):
            PHRASES[key] = (sc, dollar if prev is None else (prev[1] or dollar))


# ── CODING (plain +10) ──────────────────────────────────────────
_add(
    [
        "write code",
        "debug the code",
        "fix the bug",
        "run the server",
        "train the model",
        "push to github",
        "pull request",
        "machine learning",
        "neural network",
        "pure numpy",
        "build the app",
        "deploy the app",
        "stack overflow",
        "null pointer",
        "memory leak",
        "unit test",
        "integration test",
        "source code",
        "open source",
        "command line",
        "data structure",
        "binary search",
        "design pattern",
        "clean code",
        "refactor the function",
        "compile and run",
        "api endpoint",
        "web server",
        "database query",
        "git commit",
    ],
    10,
    False,
)

# ── HACKING (plain +10) — educational / security vocabulary only ─
_add(
    [
        "security vulnerability",
        "penetration test",
        "threat actor",
        "privilege escalation",
        "lateral movement",
        "zero day",
        "patch the system",
        "firewall rule",
        "malware analysis",
        "reverse engineering",
        "secure the endpoint",
        "credential leak",
        "phishing attempt",
        "network scan",
        "incident response",
        "blue team",
        "red team",
        "defense in depth",
        "access control",
        "encrypt the data",
    ],
    10,
    False,
)

# ── SLANG (plain +10) ───────────────────────────────────────────
_add(
    [
        "no cap",
        "for real",
        "low key",
        "high key",
        "say less",
        "what’s good",
        "whats good",
        "dead ass",
        "on god",
        "it’s giving",
        "its giving",
        "main character",
        "touch grass",
        "rent free",
        "understood the assignment",
        "let’s go",
        "lets go",
        "that’s fire",
        "thats fire",
        "mid af",
        "goated with the sauce",
        "in my bag",
        "big vibe",
        "real one",
        "stay solid",
    ],
    10,
    False,
)

# ── ATTITUDE (plain +10) ────────────────────────────────────────
_add(
    [
        "stay focused",
        "keep grinding",
        "no excuses",
        "own your path",
        "built different",
        "soft life",
        "hard work",
        "lock in",
        "boss up",
        "stand tall",
        "be real",
        "stay humble",
        "move in silence",
        "protect your energy",
        "cut the noise",
        "lead by example",
        "take the risk",
        "fearless mindset",
        "discipline over motivation",
        "cold confidence",
    ],
    10,
    False,
)

# ── STRUCTURE ( +10$ ) ──────────────────────────────────────────
_add(
    [
        "subject and verb",
        "complete sentence",
        "ask a question",
        "make a statement",
        "past tense",
        "present tense",
        "future tense",
        "noun phrase",
        "verb phrase",
        "main clause",
        "dependent clause",
        "run on sentence",
        "proper grammar",
        "word order",
        "singular and plural",
        "active voice",
        "passive voice",
        "full stop",
        "question mark",
        "capital letter",
        "the subject",
        "the predicate",
        "agree in number",
        "clear pronoun",
        "simple sentence",
        "compound sentence",
        "complex sentence",
    ],
    10,
    True,
)

# ── HUMOR ( +10$ ) ──────────────────────────────────────────────
_add(
    [
        "dark humor",
        "dad joke",
        "punch line",
        "punchline lands",
        "too soon",
        "deadpan delivery",
        "roast session",
        "cursed meme",
        "wholesome meme",
        "gallows humor",
        "absurd joke",
        "sarcastic reply",
        "dry humor",
        "bit is funny",
        "laugh out loud",
        "not that deep",
        "ironic twist",
        "comedy gold",
        "bad pun",
        "unhinged joke",
    ],
    10,
    True,
)

# ── PATTERN ( +7$ ) ─────────────────────────────────────────────
_add(
    [
        "first then",
        "cause and effect",
        "if then",
        "same as",
        "different from",
        "leads to",
        "results in",
        "because of",
        "step by step",
        "over and over",
        "again and again",
        "more and more",
        "less and less",
        "in order to",
        "as a result",
        "on the other hand",
        "for example",
        "in other words",
        "before and after",
        "one after another",
        "the more the",
        "not only but also",
        "either or",
        "both and",
        "so that",
        "even though",
        "as long as",
        "by the time",
        "pattern repeats",
        "sequence of steps",
    ],
    7,
    True,
)

# Sorted longest-first for matching
PHRASE_LIST: list[tuple[str, int, bool]] = sorted(
    [(k, v[0], v[1]) for k, v in PHRASES.items()],
    key=lambda x: len(x[0].split()),
    reverse=True,
)
