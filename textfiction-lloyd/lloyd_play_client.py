#!/usr/bin/env python3
"""Poll TextFiction LloydAgentApi and drive commands."""
from __future__ import annotations

import argparse
import json
import time
import urllib.request


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def post_command(base: str, cmd: str) -> dict:
    data = cmd.encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + "/command",
        data=data,
        method="POST",
        headers={"Content-Type": "text/plain"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Drive Lloyd TextFiction agent API")
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    print("status:", get_json(args.base + "/status"))
    for i in range(args.steps):
        st = get_json(args.base + "/state")
        text = (st.get("text") or "")[-800:]
        waiting = st.get("waiting_for_command")
        print(f"\n--- step {i+1} waiting={waiting} ---")
        print(text[-400:] if text else "(no text yet)")
        if not waiting:
            time.sleep(args.delay)
            continue
        cmd = "look" if i % 3 == 0 else ("inventory" if i % 3 == 1 else "go north")
        print(">>", cmd)
        print(post_command(args.base, cmd))
        time.sleep(args.delay)
    print("done")


if __name__ == "__main__":
    main()
