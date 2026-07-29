"""
Lloyd Task Router (original)
============================
Detects what the user wants so Lloyd can chat, draw, remember,
recall, or report status — without external APIs.
"""

from __future__ import annotations

from typing import Dict, Any
import re


def route(user_input: str) -> Dict[str, Any]:
    """
    Return {intent, payload} where intent is one of:
      chat | image | remember | recall | status | help | train_hint
    """
    text = (user_input or "").strip()
    lower = text.lower()

    if not text:
        return {"intent": "chat", "payload": text}

    # image
    if any(
        w in lower
        for w in (
            "draw",
            "paint",
            "image",
            "picture",
            "photo",
            "generate art",
            "create art",
            "make an image",
            "render",
        )
    ):
        return {"intent": "image", "payload": text}

    # explicit remember
    m = re.search(r"(?:remember|save|note)(?:\s+that)?\s+(.+)", lower)
    if m:
        return {"intent": "remember", "payload": m.group(1).strip()}

    # recall / what do you know
    if any(
        p in lower
        for p in (
            "what do you remember",
            "what do you know",
            "recall",
            "do you remember",
            "search memory",
        )
    ):
        q = re.sub(
            r"what do you (remember|know)( about)?|recall|do you remember|search memory",
            "",
            lower,
        ).strip(" ?")
        return {"intent": "recall", "payload": q or text}

    # status / who are you
    if any(
        p in lower
        for p in (
            "who are you",
            "what are you",
            "your status",
            "are you online",
            "what can you do",
            "help",
            "capabilities",
        )
    ):
        return {"intent": "status" if "help" not in lower and "what can" not in lower else "help", "payload": text}

    if "help" in lower or "what can you" in lower:
        return {"intent": "help", "payload": text}

    # train hint
    if any(p in lower for p in ("how do i train", "how to train", "train you", "upload")):
        return {"intent": "train_hint", "payload": text}

    return {"intent": "chat", "payload": text}
