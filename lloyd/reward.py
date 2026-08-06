"""
Lloyd Reward System
===================
Positive rewards when the *game* (or a correct answer) says he did right.
Win/loss for PS2 comes from the game's own built-in systems — not invented scores.
Losses still train; they just do not add fake points.
"""

from __future__ import annotations
from typing import List


class RewardSystem:
    def __init__(self):
        self.total_reward: int = 0
        self.correct_count: int = 0
        self.game_wins: int = 0
        self.game_losses: int = 0
        self.game_progress: int = 0
        self.history: List[str] = []

    def reward(self, amount: int = 5, reason: str = "correct answer") -> str:
        if amount < 0:
            amount = 0
        self.total_reward += amount
        self.correct_count += 1
        rl = reason.lower()
        if "game win" in rl or "game:win" in rl:
            self.game_wins += 1
        elif "game progress" in rl:
            self.game_progress += 1
        msg = f"reward +{amount} — {reason} | total reward: {self.total_reward}"
        self.history.append(msg)
        if len(self.history) > 200:
            self.history = self.history[-150:]
        return msg

    def note_game_loss(self, reason: str = "game lose") -> str:
        self.game_losses += 1
        msg = f"game loss recorded — {reason} | wins={self.game_wins} losses={self.game_losses}"
        self.history.append(msg)
        if len(self.history) > 200:
            self.history = self.history[-150:]
        return msg

    def status(self) -> str:
        return (
            f"rewards: {self.total_reward} | correct: {self.correct_count} | "
            f"game wins: {self.game_wins} progress: {self.game_progress} losses: {self.game_losses}"
        )

    def recent(self, n: int = 5) -> str:
        if not self.history:
            return "no rewards yet"
        return "\n".join(self.history[-n:])


rewards = RewardSystem()
