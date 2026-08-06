"""Derive win/loss/progress ONLY from the game's own rules and flags."""
from __future__ import annotations
from typing import Any, Dict, Optional

WIN_KEYS = ("win", "won", "victory", "success", "cleared", "stage_clear", "mission_complete", "goal")
LOSE_KEYS = ("lose", "lost", "loss", "fail", "failed", "death", "died", "game_over", "gameover", "defeat")
PROG_KEYS = ("checkpoint", "lap_complete", "item", "combo", "level_up", "progress")


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "win", "won")
    return bool(v)


def _num(x: Any):
    try:
        return float(x)
    except Exception:
        return None


def derive_game_outcome(
    reaction: Optional[Dict[str, Any]] = None,
    values: Optional[Dict[str, Any]] = None,
    prev_values: Optional[Dict[str, Any]] = None,
    rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Outcome comes from the game — not invented by Lloyd."""
    reaction = reaction or {}
    values = values or {}
    prev_values = prev_values or {}
    rules = rules or {}
    outcome = "neutral"
    signals = []

    for k, v in reaction.items():
        kl = str(k).lower()
        if kl in WIN_KEYS or (kl == "result" and str(v).lower() in ("win", "won", "victory")):
            if _truthy(v) or str(v).lower() in ("win", "won", "victory", "success"):
                outcome = "win"
                signals.append(f"{k}={v}")
        if kl in LOSE_KEYS or (kl == "result" and str(v).lower() in ("lose", "loss", "fail", "death")):
            if _truthy(v) or str(v).lower() in ("lose", "lost", "fail", "death", "game_over"):
                outcome = "lose"
                signals.append(f"{k}={v}")
        if kl in PROG_KEYS and _truthy(v) and outcome == "neutral":
            outcome = "progress"
            signals.append(f"{k}={v}")

    for key in ("score", "points", "money"):
        if key in values and key in prev_values:
            a, b = _num(values[key]), _num(prev_values[key])
            if a is not None and b is not None and a > b and outcome == "neutral":
                outcome = "progress"
                signals.append(f"{key}+{a - b}")

    for key in ("health", "hp", "lives"):
        if key in values and key in prev_values:
            a, b = _num(values[key]), _num(prev_values[key])
            if a is not None and b is not None and a < b:
                signals.append(f"{key}{a - b}")
                if a <= 0:
                    outcome = "lose"
                    signals.append("depleted")

    rm = rules.get("reward_map") or rules.get("_reward") or {}
    if isinstance(rm, dict):
        for label, kind in rm.items():
            v = reaction.get(label, values.get(label))
            if v is None:
                continue
            kind = str(kind).lower()
            if kind in ("win", "victory") and _truthy(v):
                outcome = "win"
                signals.append(f"rules:{label}")
            if kind in ("lose", "loss", "fail") and _truthy(v):
                outcome = "lose"
                signals.append(f"rules:{label}")

    pts = 10 if outcome == "win" else (3 if outcome == "progress" else 0)
    return {"outcome": outcome, "signals": signals[:20], "reward_pts": pts, "from_game": True}
