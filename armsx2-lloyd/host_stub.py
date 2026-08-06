#!/usr/bin/env python3
"""
Minimal host stub — push vision captions, run one agent step, drain inputs.
Run on the same network as Lloyd server (Termux, laptop, etc.).

  python armsx2-lloyd/host_stub.py
"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8080"  # change to phone IP if needed
SESSION = "demo"
GAME = "Demo"


def post(path: str, data: dict):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read().decode())


def main():
    print("Lloyd ARMSX2 host stub")
    print("BASE =", BASE)
    try:
        st = get("/emu/status")
        print("status:", st.get("emulator"), "sessions:", list((st.get("sessions") or {}).keys()))
    except Exception as e:
        print("cannot reach Lloyd:", e)
        print("start: python server.py")
        sys.exit(1)

    caption = "title screen, press start"
    if len(sys.argv) > 1:
        caption = " ".join(sys.argv[1:])

    print("push frame:", caption)
    print(post("/emu/frame", {
        "session": SESSION,
        "game": GAME,
        "caption": caption,
        "width": 640,
        "height": 448,
    }))

    print("play step:")
    print(post("/emu/play", {"session": SESSION, "goal": "start the game"}))

    print("pending inputs (apply these to ARMSX2 pad):")
    print(get(f"/emu/inputs?session={SESSION}"))

    print("learn:")
    print(post("/emu/learn", {"session": SESSION, "steps": 16}))


if __name__ == "__main__":
    main()
