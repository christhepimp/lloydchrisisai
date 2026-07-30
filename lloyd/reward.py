"""
Lloyd Reward System (positive only)
===================================
No punishment. Only rewards when he answers correctly.
"""

from __future__ import annotations
from typing import Dict, List, Optional


class RewardSystem:
    def __init__(self):
        self.total_reward: int = 0
        self.correct_count: int = 0
        self.history: List[str] = []

    def reward(self, amount: int = 5, reason: str = "correct answer") -> str:
        """Give a positive reward only."""
        if amount < 0:
            amount = 0  # never allow punishment
        self.total_reward += amount
        self.correct_count += 1
        msg = f"reward +{amount} — {reason} | total reward: {self.total_reward}"
        self.history.append(msg)
        return msg

    def status(self) -> str:
        return (
            f"rewards earned: {self.total_reward} | "
            f"correct answers: {self.correct_count}"
        )

    def recent(self, n: int = 5) -> str:
        if not self.history:
            return "no rewards yet"
        return "\n".join(self.history[-n:])


# Global instance
rewards = RewardSystem()
