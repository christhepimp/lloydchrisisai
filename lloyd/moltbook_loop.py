"""
Moltbook loop for Lloyd
=======================
- fetch feed → train on post text (always)
- optional: post / comment when enabled and key present
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lloyd.moltbook_client import MoltbookClient


class MoltbookLoop:
    def __init__(self, lloyd, client: Optional[MoltbookClient] = None):
        self.lloyd = lloyd
        self.client = client or MoltbookClient()

    def learn_from_feed(self, sort: str = "hot", limit: int = 20, steps: int = 40) -> str:
        if not self.client.configured():
            return (
                "no MOLTBOOK_API_KEY — set env or secrets.json. "
                "register first: moltbook register <name>"
            )
        data = self.client.feed(sort=sort, limit=limit)
        if data.get("error") or data.get("_http_status"):
            # try /posts fallback
            data = self.client.posts(sort=sort, limit=limit)
        texts = self.client.extract_training_texts(data)
        if not texts:
            return f"feed fetched but no train text. raw keys={list(data.keys())[:12]}"

        trained = 0
        if self.lloyd.trainer is not None:
            blob = "\n\n".join(texts)
            r = self.lloyd.trainer.train_on_text(blob, steps=steps, lr=0.007)
            trained = r.get("steps") or 0
            for t in texts[:8]:
                try:
                    self.lloyd.memory.add(f"Moltbook: {t[:200]}", {"role": "moltbook"})
                except Exception:
                    pass
        return f"moltbook learn: {len(texts)} posts → {trained} train steps"

    def post(self, title: str, content: str, submolt: str = "general") -> str:
        if not self.client.configured():
            return "no MOLTBOOK_API_KEY"
        r = self.client.create_post(title=title, content=content, submolt=submolt)
        if r.get("error") or r.get("_http_status", 200) >= 400:
            return f"post failed: {r}"
        if self.lloyd.trainer is not None:
            self.lloyd.trainer.learn_from_interaction(
                f"post to m/{submolt}: {title}", content, steps=8
            )
        return f"posted to m/{submolt}: {title} | {r}"

    def comment(self, post_id: str, content: str) -> str:
        if not self.client.configured():
            return "no MOLTBOOK_API_KEY"
        r = self.client.comment(post_id, content)
        if r.get("error") or r.get("_http_status", 200) >= 400:
            return f"comment failed: {r}"
        if self.lloyd.trainer is not None:
            self.lloyd.trainer.learn_from_interaction(
                f"comment on {post_id}", content, steps=6
            )
        return f"commented on {post_id}"

    def register(self, name: str, description: str) -> str:
        r = self.client.register(name, description)
        agent = r.get("agent") or r
        key = agent.get("api_key") or r.get("api_key")
        claim = agent.get("claim_url") or r.get("claim_url")
        code = agent.get("verification_code") or r.get("verification_code")
        if key:
            self.client.api_key = key
            # do not auto-write secrets — tell human
            return (
                f"REGISTERED name={name}\n"
                f"API_KEY={key}\n"
                f"CLAIM_URL={claim}\n"
                f"CODE={code}\n"
                f"1) save key: export MOLTBOOK_API_KEY=... or secrets.json\n"
                f"2) open claim url, verify on X\n"
                f"3) then: moltbook learn / moltbook post"
            )
        return f"register response: {r}"

    def account_status(self) -> str:
        if not self.client.configured():
            return "no key configured"
        s = self.client.status()
        me = self.client.me()
        home = self.client.home()
        return f"status={s} me={me} home_keys={list(home.keys())[:10]}"
