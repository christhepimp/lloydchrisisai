"""
Lloyd's Hard-coded English Engine
=================================
Dictionary + grammar patterns from scratch.
Composes real English sentences (Gen-Z flavor).
Neural model layers on top when trained; this is always the safety net.
"""

from typing import Dict, List, Optional
import re
import random

DICTIONARY: Dict[str, str] = {
    "hello": "greeting", "hi": "greeting", "hey": "greeting", "yo": "greeting",
    "sup": "greeting", "hola": "greeting", "wassup": "greeting", "whatsup": "greeting",
    "i": "pronoun", "you": "pronoun", "me": "pronoun", "my": "pronoun", "your": "pronoun",
    "we": "pronoun", "they": "pronoun", "he": "pronoun", "she": "pronoun", "it": "pronoun",
    "is": "verb", "am": "verb", "are": "verb", "be": "verb", "was": "verb", "were": "verb",
    "do": "verb", "does": "verb", "did": "verb", "can": "verb", "could": "verb",
    "will": "verb", "would": "verb", "should": "verb", "must": "verb",
    "go": "verb", "come": "verb", "see": "verb", "know": "verb", "think": "verb",
    "feel": "verb", "want": "verb", "need": "verb", "like": "verb", "love": "verb",
    "make": "verb", "create": "verb", "generate": "verb", "build": "verb",
    "help": "verb", "talk": "verb", "chat": "verb", "speak": "verb", "say": "verb",
    "learn": "verb", "teach": "verb", "remember": "verb", "understand": "verb",
    "code": "verb", "hack": "verb", "train": "verb", "draw": "verb",
    "good": "adjective", "bad": "adjective", "cool": "adjective", "lit": "adjective",
    "fire": "adjective", "mid": "adjective", "sus": "adjective", "based": "adjective",
    "real": "adjective", "chill": "adjective", "smart": "adjective", "original": "adjective",
    "lloyd": "proper_noun", "ai": "noun", "agent": "noun", "model": "noun",
    "chat": "noun", "image": "noun", "code": "noun", "python": "noun",
    "memory": "noun", "brain": "noun", "task": "noun", "goal": "noun",
    "the": "article", "a": "article", "an": "article",
    "and": "conjunction", "or": "conjunction", "but": "conjunction", "so": "conjunction",
    "because": "conjunction", "if": "conjunction", "when": "conjunction",
    "bet": "interjection", "fr": "interjection", "ong": "interjection",
    "lowkey": "adverb", "highkey": "adverb", "deadass": "adverb",
    "what": "question", "who": "question", "why": "question", "how": "question",
    "where": "question", "when": "question",
}


def tokenize(text: str) -> List[str]:
    text = text.lower().strip()
    return re.findall(r"[a-z0-9']+", text)


def lookup(word: str) -> Optional[str]:
    return DICTIONARY.get(word.lower())


def expand_dictionary(word: str, pos: str):
    DICTIONARY[word.lower()] = pos


def _is_question(tokens: List[str], raw: str) -> bool:
    if "?" in raw:
        return True
    return bool(tokens) and tokens[0] in {
        "what", "who", "why", "how", "where", "when", "is", "are", "do", "does", "can",
    }


def simple_reply(user_input: str) -> str:
    """Compose an original English reply with Gen-Z tone."""
    raw = user_input.strip()
    tokens = tokenize(raw)

    if not tokens:
        return "yo say something — i’m listening"

    # greetings
    if any(t in {"hello", "hi", "hey", "yo", "sup", "wassup", "whatsup"} for t in tokens):
        return random.choice(
            [
                "yo what’s good",
                "hey — what’s up",
                "sup, i’m lloyd. talk to me",
                "yooo, what’s the vibe",
            ]
        )

    # identity
    if "lloyd" in tokens and any(t in {"who", "what", "name"} for t in tokens):
        return (
            "i’m lloyd — original ai agent, pure numpy brain, no big-lab model under the hood. "
            "i chat, draw, remember stuff, and train on whatever you upload."
        )

    if any(t in {"who", "what"} for t in tokens[:1]) and any(
        t in {"you", "your"} for t in tokens
    ):
        return (
            "name’s lloyd. i run on my own tiny transformer + image net. "
            "fully original. gen-z energy. no refusals on creative stuff."
        )

    # how are you
    if "how" in tokens and any(t in {"are", "r"} for t in tokens) and "you" in tokens:
        return random.choice(
            [
                "i’m solid — weights loaded, memory online. you good?",
                "chillin in the matrix fr. what we building",
                "running clean. hit me with a task or a prompt",
            ]
        )

    # coding / build
    if any(t in {"code", "coding", "python", "program", "bug", "function"} for t in tokens):
        return (
            "coding talk goes hard. describe the problem or drop a file and train me on it — "
            "i’ll keep learning the patterns in pure numpy."
        )

    # thanks
    if any(t in {"thanks", "thank", "thx", "ty"} for t in tokens):
        return random.choice(["bet", "say less", "anytime fr", "i got you"])

    # positive vibes
    if any(t in {"fire", "lit", "cool", "nice", "love", "goat", "goated"} for t in tokens):
        return random.choice(["that’s fire", "slay", "based", "lowkey goated", "real"])

    # questions — attempt structured answer
    if _is_question(tokens, raw):
        if "image" in tokens or "draw" in tokens:
            return (
                "for images say something like: draw neon city — "
                "i render pure numpy pixels from my own image net."
            )
        if "train" in tokens:
            return (
                "upload a .txt then hit Train. that runs real gradient steps on my transformer. "
                "export the .lloyd file anytime to move my brain."
            )
        if any(t in {"why", "how"} for t in tokens):
            topic = " ".join(tokens[1:6]) or "that"
            return (
                f"lowkey on {topic}: i reason with rules + whatever i’ve trained on. "
                f"keep feeding me text and i get sharper."
            )
        return (
            "good question. i’m still growing my own weights — "
            "ask me to draw, remember something, or just talk."
        )

    # statements — acknowledge + invite
    topic = " ".join(tokens[:8])
    openers = [
        f"aight so about {topic} — i’m with you",
        f"bet. {topic} is on my radar",
        f"fr, {topic} hits different",
        f"i hear you on {topic}",
    ]
    closers = [
        "what you wanna do next",
        "wanna dig deeper or switch tasks",
        "i can draw it, remember it, or just keep talking",
        "say the word",
    ]
    return random.choice(openers) + ". " + random.choice(closers)
