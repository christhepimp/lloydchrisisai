"""
Moltbook loop for Lloyd
=======================
READ always means LEARN — every feed pull trains + stores memory.
Default: READ-ONLY (no posts). Unlock with allow_post=True.
"""

from __future__ import annotations

from typing import Optional

from lloyd.moltbook_client import MoltbookClient


class MoltbookLoop:
    def __init__(self, lloyd, client: Optional[MoltbookClient] = None):
        self.lloyd = lloyd
        self.client = client or MoltbookClient()
        self.allow_post = False

    def _always_learn(self, texts: list, steps: int = 40) -> int:
        """
        Learning is mandatory on every read/action with content:
          1) memory store
          2) importance / dictionary absorb
          3) neural train steps when trainer exists
        """
        trained = 0
        for t in texts:
            try:
                self.lloyd.memory.add(f"Moltbook: {t[:240]}", {"role": "moltbook"})
            except Exception:
                pass
            try:
                self.lloyd.importance.learn_from_text(t[:500])
            except Exception:
                pass

        if self.lloyd.trainer is not None and texts:
            try:
                blob = "\n\n".join(texts)
                r = self.lloyd.trainer.train_on_text(blob, steps=steps, lr=0.007)
                trained = int(r.get("steps") or 0)
            except Exception:
                try:
                    if hasattr(self.lloyd.trainer, "learn_from_interaction"):
                        for t in texts[:6]:
                            self.lloyd.trainer.learn_from_interaction(
                                "moltbook read", t[:400], steps=max(4, steps // 6)
                            )
                            trained += max(4, steps // 6)
                except Exception:
                    pass
        return trained

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

        # READ ⇒ LEARN always
        trained = self._always_learn(texts, steps=steps)
        mode = "read-only" if not self.allow_post else "read+write"
        return (
            f"moltbook learn ({mode}): read {len(texts)} posts → "
            f"ALWAYS learned | {trained} train steps + memory + importance"
        )

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
        # doing something ⇒ learn from it
        self._always_learn([f"{title}\n{content}"], steps=12)
        return f"posted to m/{submolt}: {title} | learned from own post | {r}"

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
        self._always_learn([f"comment on {post_id}: {content}"], steps=10)
        return f"commented on {post_id} | learned from comment"

    def set_read_only(self, read_only: bool = True) -> str:
        self.allow_post = not read_only
        if self.allow_post:
            return "moltbook WRITE enabled — post/comment allowed (still learns on every action)"
        return "moltbook READ-ONLY — every read still learns, no post/comment"

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
                f"3) moltbook learn / free on (read always learns)"
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
