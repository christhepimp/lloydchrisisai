"""
Moltbook loop for Lloyd
=======================
Default: READ-ONLY — fetch feed + train. No posts/comments.
Unlock writing only with allow_post=True or chat: moltbook allow post
"""

from __future__ import annotations

from typing import Optional

from lloyd.moltbook_client import MoltbookClient


class MoltbookLoop:
    def __init__(self, lloyd, client: Optional[MoltbookClient] = None):
        self.lloyd = lloyd
        self.client = client or MoltbookClient()
        # read-only by default — he learns, he does not post
        self.allow_post = False

    def learn_from_feed(self, sort: str = "hot", limit: int = 20, steps: int = 40) -> str:
        if not self.client.configured():
            return (
                "no MOLTBOOK_API_KEY — set env or secrets.json. "
                "register first: moltbook register <name>"
            )
        data = self.client.feed(sort=sort, limit=limit)
        if data.get("error") or data.get("_http_status"):
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
        mode = "read-only" if not self.allow_post else "read+write"
        return f"moltbook learn ({mode}): {len(texts)} posts → {trained} train steps"

    def post(self, title: str, content: str, submolt: str = "general") -> str:
        if not self.allow_post:
            return (
                "moltbook is READ-ONLY — posting blocked. "
                "he can only learn (moltbook learn). "
                "to allow posts: moltbook allow post"
            )
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
        if not self.allow_post:
            return (
                "moltbook is READ-ONLY — comments blocked. "
                "use: moltbook learn"
            )
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

    def set_read_only(self, read_only: bool = True) -> str:
        self.allow_post = not read_only
        if self.allow_post:
            return "moltbook WRITE enabled — post/comment allowed"
        return "moltbook READ-ONLY — learn only, no post/comment"

    def register(self, name: str, description: str) -> str:
        r = self.client.register(name, description)
        agent = r.get("agent") or r
        key = agent.get("api_key") or r.get("api_key")
        claim = agent.get("claim_url") or r.get("claim_url")
        code = agent.get("verification_code") or r.get("verification_code")
        if key:
            self.client.api_key = key
            return (
                f"REGISTERED name={name}\n"
                f"API_KEY={key}\n"
                f"CLAIM_URL={claim}\n"
                f"CODE={code}\n"
                f"1) save key in secrets.json\n"
                f"2) claim on X\n"
                f"3) moltbook learn (read-only by default)"
            )
        return f"register response: {r}"

    def account_status(self) -> str:
        if not self.client.configured():
            return "no key configured"
        s = self.client.status()
        me = self.client.me()
        home = self.client.home()
        mode = "WRITE" if self.allow_post else "READ-ONLY"
        return f"mode={mode} status={s} me={me} home_keys={list(home.keys())[:10]}"
