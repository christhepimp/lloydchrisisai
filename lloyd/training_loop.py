"""
Lloyd Interactive Training Loop
===============================
Not a PDF. A live program that asks questions, gives a couple free answers,
then makes him use patterns. Wrong → self-reflection. Correct → reward only.

In AI terms the reflection part is called:
  Self-reflection / Reflexion / metacognition / error analysis
"""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from lloyd.importance import teach_equals, engine as importance_engine
from lloyd.reward import rewards
from lloyd.reflection import reflector


# ──────────────────────────────────────────────
# Training data (stories + questions)
# ──────────────────────────────────────────────

LESSONS = [
    # ---- FREE ANSWER ROUND 1 ----
    {
        "id": 1,
        "phase": "free",
        "title": "Story 1 — The Dog (free answer)",
        "story": (
            "The sun was out. A bird flew by. Someone walked past the house.\n"
            "The dog barked. ∆the dog barked+20∆\n"
            "The dog ate. ∆the dog ate+20∆\n"
            "The dog ran. ∆the dog ran+20∆\n"
            "Later it got quiet again."
        ),
        "equals": [("dog", "animal")],
        "question": "The dog ______?",
        "correct": ["barked", "ate", "ran", "the dog barked", "the dog ate", "the dog ran"],
        "give_answer": "the dog barked",
        "hint": "the parts with +20 are the important actions of the dog",
    },
    # ---- FREE ANSWER ROUND 2 ----
    {
        "id": 2,
        "phase": "free",
        "title": "Story 2 — The Cat (free answer)",
        "story": (
            "It was a calm afternoon. A car drove by. Leaves moved in the wind.\n"
            "The cat ate. ∆the cat ate+20∆\n"
            "The cat walked. ∆the cat walked+15∆\n"
            "The cat sat. ∆the cat sat+10∆\n"
            "Then everything was still."
        ),
        "equals": [("cat", "animal")],
        "question": "The cat ______?",
        "correct": ["ate", "walked", "sat", "the cat ate", "the cat walked", "the cat sat"],
        "give_answer": "the cat ate",
        "hint": "the parts with + numbers are the important actions of the cat",
    },
    # ---- NO FREE ANSWER — must use pattern ----
    {
        "id": 3,
        "phase": "pattern",
        "title": "Story 3 — The Pig (no free answer — use the pattern)",
        "story": (
            "The dog was walking down the street. ∆dog was walking+20∆\n"
            "As the dog walked the dog stared. ∆the dog stared+20∆\n"
            "Then the dog sat and ate. ∆the dog ate+20∆\n"
            "\n"
            "∆dog=animal∆\n"
            "∆pig=animal∆"
        ),
        "equals": [("dog", "animal"), ("pig", "animal")],
        "question": "The pig ______?",
        "correct": [
            "was walking", "stared", "ate",
            "the pig was walking", "the pig stared", "the pig ate",
            "pig was walking", "pig stared", "pig ate",
        ],
        "give_answer": None,  # no free answer
        "hint": "dog equals animal, pig equals animal. the + actions on the dog transfer to the pig",
    },
]


class TrainingLoop:
    def __init__(self):
        self.index = 0
        self.finished = False
        self.waiting_for_answer = False
        self.current: Optional[Dict] = None

    def start(self) -> str:
        self.index = 0
        self.finished = False
        return self._present_current()

    def _present_current(self) -> str:
        if self.index >= len(LESSONS):
            self.finished = True
            return (
                "training loop complete.\n"
                f"{rewards.status()}\n"
                "you went through free answers → reward, then a pattern question with no free answer."
            )

        lesson = LESSONS[self.index]
        self.current = lesson
        self.waiting_for_answer = True

        # Teach equals and importance from the story text
        for a, b in lesson.get("equals", []):
            teach_equals(a, b)
        importance_engine.learn_from_text(lesson["story"])

        lines = [
            f"=== {lesson['title']} ===",
            "",
            lesson["story"],
            "",
            f"QUESTION: {lesson['question']}",
        ]

        if lesson["phase"] == "free" and lesson.get("give_answer"):
            lines.append("")
            lines.append(f"(free answer given so you can succeed): {lesson['give_answer']}")
            lines.append("type that answer (or another correct one) to earn reward.")
        else:
            lines.append("")
            lines.append("(no free answer — use the pattern: what equals what + the + importance parts)")

        return "\n".join(lines)

    def submit_answer(self, answer: str) -> str:
        if self.finished or not self.waiting_for_answer or self.current is None:
            return "no active question. type 'start training' to begin."

        lesson = self.current
        ans = answer.strip().lower()
        correct_list = [c.lower() for c in lesson["correct"]]

        # Check correctness
        is_correct = any(
            ans == c or ans.endswith(c) or c in ans
            for c in correct_list
        )

        if is_correct:
            reward_msg = rewards.reward(5, reason=f"correct on: {lesson['question']}")
            reflect_note = reflector.on_correct(ans)
            self.waiting_for_answer = False
            self.index += 1
            next_part = self._present_current()
            return (
                f"correct.\n{reward_msg}\n{reflect_note}\n\n"
                f"--- next ---\n{next_part}"
            )
        else:
            # Wrong → self-reflection (no punishment)
            reflection = reflector.on_wrong(
                question=lesson["question"],
                his_answer=ans,
                correct_hint=lesson.get("hint", ""),
            )
            return (
                f"not the target answer.\n\n"
                f"{reflection}\n\n"
                f"try again. question is still: {lesson['question']}"
            )

    def status(self) -> str:
        return (
            f"lesson {self.index + 1}/{len(LESSONS)} | "
            f"waiting={self.waiting_for_answer} | "
            f"{rewards.status()}"
        )


# Global training loop instance
training = TrainingLoop()
