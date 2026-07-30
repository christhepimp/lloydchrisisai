"""
Lloyd Self-Reflection / Error Analysis
======================================
In AI this is commonly called:
  - Self-reflection
  - Reflexion (agent reflects on its own failures)
  - Metacognition
  - Error analysis / error-driven learning
  - Credit assignment (what led to the outcome)

When Lloyd answers wrong he asks himself why,
then notices what leads to the right answer.
No punishment — only reflection + later reward on success.
"""

from __future__ import annotations
from typing import List, Optional, Tuple


class ReflectionEngine:
    def __init__(self):
        self.last_wrong: Optional[str] = None
        self.last_question: Optional[str] = None
        self.reflections: List[str] = []

    def on_wrong(self, question: str, his_answer: str, correct_hint: str = "") -> str:
        """
        Called when an answer is wrong.
        Lloyd asks himself why and looks for what would lead to the right answer.
        """
        self.last_wrong = his_answer
        self.last_question = question

        reflection = (
            f"i got that wrong. asking myself why...\n"
            f"question was about: {question}\n"
            f"my answer: {his_answer}\n"
        )

        if correct_hint:
            reflection += (
                f"what leads to the right answer looks more like: {correct_hint}\n"
                f"difference i notice: i should focus on the parts marked important (+) "
                f"and on what equals what.\n"
            )
        else:
            reflection += (
                "i need to look at the + importance markers and the equals links "
                "to see what actually leads to the correct answer.\n"
            )

        reflection += "no punishment — just learning from the miss."
        self.reflections.append(reflection)
        return reflection

    def on_correct(self, answer: str) -> str:
        """Light positive note after a correct answer (reward is handled separately)."""
        note = f"that matched the pattern. my answer '{answer}' lined up with the important parts."
        self.reflections.append(note)
        return note

    def status(self) -> str:
        if not self.reflections:
            return "no reflections yet"
        return "last reflection:\n" + self.reflections[-1]


# Global instance
reflector = ReflectionEngine()
