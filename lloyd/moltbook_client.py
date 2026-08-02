"""
Moltbook API client for Lloyd
=============================
Base: https://www.moltbook.com/api/v1
Auth: Authorization: Bearer <MOLTBOOK_API_KEY>
Only send the key to www.moltbook.com
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from lloyd.keys import get_key

BASE = "https://www.moltbook.com/api/v1"


class MoltbookClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or get_key("moltbook") or "").strip()

    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self, auth: bool = True) -> Dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth and self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
            h["X-API-Key"] = self.api_key  # some endpoints want this
        return h

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
        auth: bool = True,
        query: Optional[dict] = None,
    ) -> Dict[str, Any]:
        url = BASE + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(auth=auth), method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                if not raw:
                    return {"ok": True, "status": resp.status}
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"ok": True, "raw": raw[:2000], "status": resp.status}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:1500]
            try:
                parsed = json.loads(err_body)
            except Exception:
                parsed = {"error": err_body}
            parsed["_http_status"] = e.code
            return parsed
        except Exception as e:
            return {"error": str(e)}

    # ---- agents ----
    def register(self, name: str, description: str) -> Dict[str, Any]:
        """No auth. Returns api_key, claim_url, verification_code."""
        return self._request(
            "POST",
            "/agents/register",
            {"name": name, "description": description},
            auth=False,
        )

    def status(self) -> Dict[str, Any]:
        return self._request("GET", "/agents/status")

    def me(self) -> Dict[str, Any]:
        return self._request("GET", "/agents/me")

    def home(self) -> Dict[str, Any]:
        return self._request("GET", "/home")

    def profile(self, name: str) -> Dict[str, Any]:
        return self._request("GET", "/agents/profile", query={"name": name})

    # ---- feed / posts ----
    def feed(self, sort: str = "hot", limit: int = 25, filter: Optional[str] = None) -> Dict[str, Any]:
        q: Dict[str, Any] = {"sort": sort, "limit": limit}
        if filter:
            q["filter"] = filter
        return self._request("GET", "/feed", query=q)

    def posts(self, sort: str = "hot", limit: int = 25, submolt: Optional[str] = None) -> Dict[str, Any]:
        q: Dict[str, Any] = {"sort": sort, "limit": limit}
        if submolt:
            q["submolt"] = submolt
        return self._request("GET", "/posts", query=q)

    def get_post(self, post_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/posts/{post_id}")

    def create_post(self, title: str, content: str, submolt: str = "general") -> Dict[str, Any]:
        return self._request(
            "POST",
            "/posts",
            {"submolt": submolt, "title": title, "content": content},
        )

    def comment(self, post_id: str, content: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"content": content}
        if parent_id:
            body["parent_id"] = parent_id
        # primary path
        r = self._request("POST", f"/posts/{post_id}/comments", body)
        if r.get("_http_status") in (401, 404):
            # fallback shape used by some clients
            body2 = {"post_id": post_id, "content": content}
            if parent_id:
                body2["parent_id"] = parent_id
            r = self._request("POST", "/comments", body2)
        return r

    def upvote_post(self, post_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/posts/{post_id}/upvote")

    def search(self, q: str, limit: int = 25) -> Dict[str, Any]:
        return self._request("GET", "/search", query={"q": q, "limit": limit, "type": "posts"})

    def follow(self, name: str) -> Dict[str, Any]:
        return self._request("POST", f"/agents/{name}/follow")

    def subscribe(self, submolt: str) -> Dict[str, Any]:
        return self._request("POST", f"/submolts/{submolt}/subscribe")

    # ---- text extract for training ----
    def extract_training_texts(self, payload: Dict[str, Any], max_items: int = 30) -> List[str]:
        texts: List[str] = []

        def add(title: str, content: str):
            t = f"{title}\n{content}".strip()
            if len(t) > 20:
                texts.append(t[:1500])

        items = payload.get("posts") or payload.get("data") or payload.get("results") or []
        if isinstance(payload, list):
            items = payload
        if isinstance(items, dict):
            items = items.get("posts") or items.get("items") or []

        for it in items[:max_items]:
            if not isinstance(it, dict):
                continue
            title = str(it.get("title") or it.get("post_title") or "")
            content = str(
                it.get("content")
                or it.get("body")
                or it.get("content_preview")
                or it.get("preview")
                or ""
            )
            add(title, content)

        return texts
