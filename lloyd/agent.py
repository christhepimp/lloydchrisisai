"""
Lloyd - Autonomous Agent Core
=============================
This is the brain that decides what to do.
"""

from lloyd.english_engine import simple_reply, expand_dictionary
from lloyd.personality import get_system_prompt, apply_genz_style
from lloyd.memory import VectorMemory
from typing import Optional
import random


class Lloyd:
    def __init__(self):
        self.memory = VectorMemory(dim=32)
        self.goals = [
            "improve my english dictionary and grammar rules",
            "generate images when i feel creative",
            "grow my personal memory of conversations and facts",
        ]
        self.system_prompt = get_system_prompt()
        print("Lloyd is online. No censorship. Autonomous mode active.")

    def think(self, user_input: str) -> str:
        # Store the interaction
        self.memory.add(f"User: {user_input}", {"role": "user"})

        # Very basic autonomous decision (will get smarter)
        if random.random() < 0.15:
            # Sometimes pursue a goal unprompted
            goal = random.choice(self.goals)
            reply = f"lowkey thinking about my goal rn: {goal}"
        else:
            reply = simple_reply(user_input)

        reply = apply_genz_style(reply)
        self.memory.add(f"Lloyd: {reply}", {"role": "lloyd"})

        return reply

    def remember(self, text: str):
        self.memory.add(text)

    def recall(self, query: str, top_k: int = 3):
        return self.memory.search(query, top_k=top_k)

    def add_word(self, word: str, pos: str):
        expand_dictionary(word, pos)
        self.memory.add(f"Learned new word: {word} ({pos})")
