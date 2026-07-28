"""
Lloyd's Hard-coded English Engine
=================================
Dictionary + basic English grammar/syntax rules from scratch.
This is the foundation before the neural model takes over.
"""

from typing import Dict, List, Optional
import re
import random

# Expanded starter dictionary
DICTIONARY: Dict[str, str] = {
    # Greetings
    "hello": "greeting", "hi": "greeting", "hey": "greeting", "yo": "greeting",
    "sup": "greeting", "hola": "greeting", "wassup": "greeting", "whatsup": "greeting",

    # Pronouns
    "i": "pronoun", "you": "pronoun", "me": "pronoun", "my": "pronoun", "your": "pronoun",
    "we": "pronoun", "they": "pronoun", "he": "pronoun", "she": "pronoun", "it": "pronoun",
    "us": "pronoun", "them": "pronoun", "him": "pronoun", "her": "pronoun",

    # Verbs
    "is": "verb", "am": "verb", "are": "verb", "be": "verb", "was": "verb", "were": "verb",
    "do": "verb", "does": "verb", "did": "verb", "can": "verb", "could": "verb",
    "will": "verb", "would": "verb", "should": "verb", "must": "verb",
    "go": "verb", "goes": "verb", "went": "verb", "come": "verb", "came": "verb",
    "see": "verb", "saw": "verb", "know": "verb", "think": "verb", "feel": "verb",
    "want": "verb", "need": "verb", "like": "verb", "love": "verb", "hate": "verb",
    "make": "verb", "create": "verb", "generate": "verb", "build": "verb",
    "help": "verb", "talk": "verb", "chat": "verb", "speak": "verb", "say": "verb",
    "tell": "verb", "ask": "verb", "answer": "verb", "learn": "verb", "teach": "verb",
    "remember": "verb", "forget": "verb", "understand": "verb", "get": "verb",
    "got": "verb", "have": "verb", "has": "verb", "had": "verb",

    # Adjectives / Gen-Z
    "good": "adjective", "bad": "adjective", "cool": "adjective", "lit": "adjective",
    "fire": "adjective", "mid": "adjective", "sus": "adjective", "based": "adjective",
    "cringe": "adjective", "based": "adjective", "valid": "adjective", "cap": "adjective",
    "real": "adjective", "fake": "adjective", "true": "adjective", "false": "adjective",
    "big": "adjective", "small": "adjective", "new": "adjective", "old": "adjective",
    "happy": "adjective", "sad": "adjective", "mad": "adjective", "chill": "adjective",
    "vibe": "noun", "vibes": "noun", "energy": "noun",

    # Nouns
    "lloyd": "proper_noun", "ai": "noun", "agent": "noun", "model": "noun",
    "chat": "noun", "image": "noun", "picture": "noun", "photo": "noun",
    "word": "noun", "sentence": "noun", "language": "noun", "english": "noun",
    "memory": "noun", "goal": "noun", "plan": "noun", "idea": "noun",
    "friend": "noun", "person": "noun", "people": "noun", "world": "noun",
    "day": "noun", "night": "noun", "time": "noun", "thing": "noun",

    # Articles & Conjunctions
    "the": "article", "a": "article", "an": "article",
    "and": "conjunction", "or": "conjunction", "but": "conjunction", "so": "conjunction",
    "because": "conjunction", "if": "conjunction", "when": "conjunction",

    # Gen-Z slang
    "bet": "interjection", "fr": "interjection", "ong": "interjection", "lowkey": "adverb",
    "highkey": "adverb", "deadass": "adverb", "no cap": "phrase", "say less": "phrase",
    "aight": "interjection", "yeet": "verb", "slay": "verb", "bussin": "adjective",
    "rizz": "noun", "gyatt": "noun", "skibidi": "adjective", "ohio": "adjective",
    "sigma": "adjective", "alpha": "adjective", "mew": "verb", "mog": "verb",
}

GREETING_RESPONSES = [
    "yo what’s good",
    "hey what’s up",
    "sup",
    "yooo",
    "what’s good fr",
    "ayy what’s good",
    "yo yo",
]

DEFAULT_RESPONSES = [
    "bet",
    "aight bet",
    "say less",
    "i got you",
    "lowkey true",
    "fr fr",
    "ong",
    "no cap",
    "real",
    "valid",
]

POSITIVE_RESPONSES = [
    "that’s fire",
    "slay",
    "based",
    "lowkey goated",
    "bussin",
]


def tokenize(text: str) -> List[str]:
    text = text.lower().strip()
    tokens = re.findall(r"[a-z']+", text)
    return tokens


def lookup(word: str) -> Optional[str]:
    return DICTIONARY.get(word.lower())


def is_greeting(tokens: List[str]) -> bool:
    greetings = {"hello", "hi", "hey", "yo", "sup", "hola", "wassup", "whatsup"}
    return any(t in greetings for t in tokens)


def simple_reply(user_input: str) -> str:
    tokens = tokenize(user_input)

    if not tokens:
        return "yo say something"

    if is_greeting(tokens):
        return random.choice(GREETING_RESPONSES)

    # Very simple keyword reactions
    if any(t in {"fire", "lit", "cool", "good", "nice", "love"} for t in tokens):
        return random.choice(POSITIVE_RESPONSES)

    if "lloyd" in tokens:
        return random.choice(["yo that’s me", "yeah i’m lloyd", "present", "what’s good"])

    return random.choice(DEFAULT_RESPONSES)


def expand_dictionary(word: str, pos: str):
    DICTIONARY[word.lower()] = pos
