"""
Lloyd API Keys
==============
Load secrets from environment variables and optional secrets.json.
Never commit real keys. Copy secrets.example.json → secrets.json locally.

Supported keys (env name → config field):
  MOLTBOOK_API_KEY
  OPENAI_API_KEY
  ANTHROPIC_API_KEY
  OPENROUTER_API_KEY
  XAI_API_KEY
  GROQ_API_KEY
  GOOGLE_API_KEY
  SERPER_API_KEY
  BRAVE_API_KEY
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

_ROOT = Path(__file__).resolve().parent.parent
_SECRETS_PATHS = [
    _ROOT / "secrets.json",
    Path.home() / ".config" / "lloyd" / "secrets.json",
    Path.home() / ".config" / "moltbook" / "credentials.json",
]

_ENV_MAP = {
    "moltbook": "MOLTBOOK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "xai": "XAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "google": "GOOGLE_API_KEY",
    "serper": "SERPER_API_KEY",
    "brave": "BRAVE_API_KEY",
}


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def load_keys() -> Dict[str, str]:
    """Merge secrets file + env. Env wins."""
    data: Dict[str, str] = {}
    for p in _SECRETS_PATHS:
        raw = _read_json(p)
        # support {"api_key": "..."} moltbook style
        if "api_key" in raw and "moltbook" not in data:
            data["moltbook"] = str(raw["api_key"])
        if "moltbook_api_key" in raw:
            data["moltbook"] = str(raw["moltbook_api_key"])
        for k, v in raw.items():
            if isinstance(v, str) and v.strip() and k not in ("api_key",):
                key = k.lower().replace("_api_key", "").replace("_key", "")
                data[key] = v.strip()

    for field, env_name in _ENV_MAP.items():
        val = os.environ.get(env_name, "").strip()
        if val:
            data[field] = val
    return data


def get_key(name: str) -> Optional[str]:
    keys = load_keys()
    return keys.get(name.lower()) or keys.get(name.lower().replace("_api_key", ""))


def has_key(name: str) -> bool:
    return bool(get_key(name))


def status() -> str:
    keys = load_keys()
    present = [k for k, v in keys.items() if v]
    missing = [k for k in _ENV_MAP if k not in present]
    return (
        f"api keys loaded: {', '.join(present) or 'none'} | "
        f"not set: {', '.join(missing) or '—'}"
    )
