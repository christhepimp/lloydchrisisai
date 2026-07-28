"""
Lloyd's Hard-coded English Engine
=================================
Dictionary + basic English grammar/syntax rules from scratch.
This is the foundation before the neural model takes over.
"""

from typing import Dict, List, Optional
import re

# Extremely small starter dictionary (we will expand this heavily)
DICTIONARY: Dict[str, str] = {
    "hello": "greeting",
    "hi": "greeting",
    "hey": "greeting",
    "yo": "greeting",
    "sup": "greeting",
    "good": "adjective",
    "bad": "adjective",
    "cool": "adjective",
    "lit": "adjective",
    "fire": "adjective",
    "mid": "adjective",
    "sus": "adjective",
    "based": "adjective",
    "i": "pronoun",
    "you": "pronoun",
    "me": "pronoun",
    "my": "pronoun",
    "your": "pronoun",
    "is": "verb",
    "am": "verb",
    "are": "verb",
    "be": "verb",
    "do": "verb",
    "can": "verb",
    "will": "verb",
    "the": "article",
    "a": "article",
    "an": "article",
    "and": "conjunction",
    "or": "conjunction",
    "but": "conjunction",
    "lloyd": "proper_noun",
    "ai": "noun",
    "agent": "noun",
    "model": "noun",
    "chat": "noun",
    "image": "noun",
    "generate": "verb",
    "create": "verb",
    "make": "verb",
    "help": "verb",
    "know": "verb",
    "think": "verb",
    "feel": "verb",
    "want": "verb",
    "need": "verb",
    "like": "verb",
    "love": "verb",
    "hate": "verb",
}

# Very basic response templates (will be replaced by the real model)
GREETING_RESPONSES = [
    "yo what’s good",
    "hey what’s up",
    "sup",
    "yooo",
    "what’s good fr",
]

DEFAULT_RESPONSES = [
    "bet",
    "aight bet",
    "say less",
    "i got you",
    "lowkey true",
    "fr fr",
    "ong",
]


def tokenize(text: str) -> List[str]:
    text = text.lower().strip()
    # Simple split on non-letters
    tokens = re.findall(r"[a-z']+", text)
    return tokens


def lookup(word: str) -> Optional[str]:
    return DICTIONARY.get(word.lower())


def is_greeting(tokens: List[str]) -> bool:
    greetings = {"hello", "hi", "hey", "yo", "sup", "hola"}
    return any(t in greetings for t in tokens)


def simple_reply(user_input: str) -> str:
    """
    Extremely basic rule-based reply using the hard-coded dictionary.
    This is only the bootstrap until the Transformer starts generating real text.
    """
    tokens = tokenize(user_input)

    if not tokens:
        return "yo say something"

    if is_greeting(tokens):
        import random
        return random.choice(GREETING_RESPONSES)

    # Very dumb fallback for now
    import random
    return random.choice(DEFAULT_RESPONSES)


def expand_dictionary(word: str, pos: str):
    """Allow Lloyd (or us) to grow the dictionary over time."""
    DICTIONARY[word.lower()] = pos
