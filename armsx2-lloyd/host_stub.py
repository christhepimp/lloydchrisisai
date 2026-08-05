#!/usr/bin/env python3
"""
Minimal host-side stub for ARMSX2 ↔ Lloyd.
Push vision captions (or frames) while you play; poll controller queue.
Map returned buttons/sticks to virtual pad / ADB / future ARMSX2 plugin.

Usage:
  python armsx2-lloyd/host_stub.py
  # or import and call post/get from your capture script
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Dict, List

BASE = "http://127.0.0.1:8080"


def post(path: str, data: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get(path: str) -> Dict[str, Any]:
    with urllib.request.urlopen(BASE + path, timeout=15) as resp:
        return json.loads(resp.read())


def push_frame(
    session: str = "demo",
    game: str = "Demo",
    caption: str = "",
    image_b64: str = "",
    width: int = 0,
    height: int = 0,
) -> Dict[str, Any]:
    return post(
        "/emu/frame",
        {
            "session": session,
            "game": game,
            "caption": caption,
            "image_b64": image_b64,
            "width": width,
            "height": height,
        },
    )


def push_audio(session: str = "demo", transcript: str = "", level: float = 0.0) -> Dict[str, Any]:
    return post(
        "/emu/audio",
        {"session": session, "transcript": transcript, "level": level},
    )


def agent_play(session: str = "demo", goal: str = "progress") -> Dict[str, Any]:
    return post("/emu/play", {"session": session, "goal": goal})


def drain_inputs(session: str = "demo") -> List[Dict[str, Any]]:
    return get(f"/emu/inputs?session={session}").get("inputs") or []


def learn(session: str = "demo", steps: int = 24) -> Dict[str, Any]:
    return post("/emu/learn", {"session": session, "steps": steps})


def demo_loop():
    print("Lloyd ARMSX2 host stub — simulating one vision → play → input drain → learn")
    print(push_frame(caption="title screen, press start to begin", game="Stub Game"))
    print(agent_play(goal="start the game"))
    inputs = drain_inputs()
    print("pending inputs for emulator:", inputs)
    print(learn())
    print("done. Point real capture at push_frame / drain_inputs.")


if __name__ == "__main__":
    demo_loop()
