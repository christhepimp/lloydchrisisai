"""
Lloyd MCP client — connect to emulator MCP servers (mcp-pine / PCSX2-MCP / any stdio MCP).

Typical path on Android / desktop:

  Lloyd  --stdio MCP-->  mcp-pine  --PINE-->  ARMSX2 or PCSX2

stdlib only (no mcp SDK required). Supports:
  - stdio transport (spawn mcp-pine / npx mcp-pine)
  - simple HTTP JSON-RPC POST (optional Streamable-style single-shot)
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_mcp_config() -> dict:
    cfg: Dict[str, Any] = {
        "enabled": False,
        "transport": "stdio",  # stdio | http
        "command": "npx",
        "args": ["-y", "mcp-pine"],
        "env": {
            "PINE_TARGET": "pcsx2",
            "PINE_SLOT": "28011",
            "PINE_HOST": "127.0.0.1",
        },
        "http_url": "",
        "timeout_s": 20.0,
    }
    for name in ("secrets.json", "mcp.json", "mcp_config.json"):
        p = Path(name)
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        block = data.get("mcp") or data.get("mcp_pine") or {}
        if isinstance(block, dict):
            cfg.update({k: v for k, v in block.items() if v is not None})
        # top-level shortcuts
        if data.get("mcp_enabled") is not None:
            cfg["enabled"] = bool(data["mcp_enabled"])
        if data.get("mcp_command"):
            cfg["command"] = data["mcp_command"]
        if data.get("mcp_http_url"):
            cfg["http_url"] = data["mcp_http_url"]
            cfg["transport"] = "http"
    # env overrides
    if os.environ.get("LLOYD_MCP_ENABLED", "").lower() in ("1", "true", "yes"):
        cfg["enabled"] = True
    if os.environ.get("LLOYD_MCP_COMMAND"):
        cfg["command"] = os.environ["LLOYD_MCP_COMMAND"]
    if os.environ.get("LLOYD_MCP_HTTP"):
        cfg["http_url"] = os.environ["LLOYD_MCP_HTTP"]
        cfg["transport"] = "http"
    for k in ("PINE_TARGET", "PINE_SLOT", "PINE_HOST", "PINE_SOCKET_PATH"):
        if os.environ.get(k):
            cfg.setdefault("env", {})[k] = os.environ[k]
    return cfg


class MCPClient:
    """Minimal MCP client (tools/list + tools/call)."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or _load_mcp_config()
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._id = 0
        self._initialized = False
        self._tools: List[dict] = []
        self.last_error = ""
        self.connected = False

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def enabled(self) -> bool:
        return bool(self.config.get("enabled"))

    def status(self) -> dict:
        return {
            "enabled": self.enabled(),
            "connected": self.connected,
            "transport": self.config.get("transport"),
            "command": self.config.get("command"),
            "args": self.config.get("args"),
            "http_url": self.config.get("http_url") or None,
            "tools": [t.get("name") for t in self._tools],
            "tool_count": len(self._tools),
            "initialized": self._initialized,
            "last_error": self.last_error or None,
            "pine_env": {
                k: (self.config.get("env") or {}).get(k)
                for k in ("PINE_TARGET", "PINE_SLOT", "PINE_HOST")
            },
        }

    def connect(self) -> dict:
        if not self.enabled():
            return {"ok": False, "error": "mcp disabled — set secrets.json mcp.enabled=true or LLOYD_MCP_ENABLED=1"}
        transport = (self.config.get("transport") or "stdio").lower()
        try:
            if transport == "http":
                return self._connect_http()
            return self._connect_stdio()
        except Exception as e:
            self.last_error = str(e)
            self.connected = False
            return {"ok": False, "error": str(e)}

    def disconnect(self) -> dict:
        with self._lock:
            if self._proc is not None:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=2)
                except Exception:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
                self._proc = None
            self._initialized = False
            self.connected = False
            self._tools = []
        return {"ok": True, "connected": False}

    def _connect_stdio(self) -> dict:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None and self._initialized:
                return {"ok": True, "connected": True, "tools": [t.get("name") for t in self._tools]}

            self.disconnect()
            cmd = self.config.get("command") or "npx"
            args = list(self.config.get("args") or ["-y", "mcp-pine"])
            env = os.environ.copy()
            for k, v in (self.config.get("env") or {}).items():
                if v is not None:
                    env[str(k)] = str(v)

            self._proc = subprocess.Popen(
                [cmd] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                bufsize=0,
            )
            # initialize
            init = self._rpc_stdio(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "lloyd", "version": "0.19"},
                },
            )
            if init.get("error"):
                self.last_error = str(init["error"])
                self.disconnect()
                return {"ok": False, "error": self.last_error, "raw": init}

            # notifications/initialized (no response expected)
            self._notify_stdio("notifications/initialized", {})

            listed = self._rpc_stdio("tools/list", {})
            tools = []
            if isinstance(listed, dict):
                result = listed.get("result") or {}
                tools = result.get("tools") or []
            self._tools = tools if isinstance(tools, list) else []
            self._initialized = True
            self.connected = True
            self.last_error = ""
            return {
                "ok": True,
                "connected": True,
                "transport": "stdio",
                "tools": [t.get("name") for t in self._tools],
                "init": (init.get("result") or {}),
            }

    def _connect_http(self) -> dict:
        url = (self.config.get("http_url") or "").strip()
        if not url:
            return {"ok": False, "error": "mcp http_url empty"}
        init = self._rpc_http(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "lloyd", "version": "0.19"},
            },
        )
        if init.get("error") and not init.get("result"):
            self.last_error = str(init.get("error"))
            self.connected = False
            return {"ok": False, "error": self.last_error, "raw": init}
        listed = self._rpc_http("tools/list", {})
        tools = []
        if isinstance(listed, dict):
            result = listed.get("result") or listed
            tools = result.get("tools") or []
        self._tools = tools if isinstance(tools, list) else []
        self._initialized = True
        self.connected = True
        self.last_error = ""
        return {
            "ok": True,
            "connected": True,
            "transport": "http",
            "tools": [t.get("name") for t in self._tools],
        }

    def list_tools(self) -> List[dict]:
        if not self.connected:
            self.connect()
        return list(self._tools)

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        if not self.connected:
            conn = self.connect()
            if not conn.get("ok"):
                return conn
        args = arguments or {}
        transport = (self.config.get("transport") or "stdio").lower()
        if transport == "http":
            resp = self._rpc_http("tools/call", {"name": name, "arguments": args})
        else:
            resp = self._rpc_stdio("tools/call", {"name": name, "arguments": args})
        if resp.get("error"):
            self.last_error = str(resp["error"])
            return {"ok": False, "error": resp["error"], "tool": name}
        result = resp.get("result") or resp
        # normalize MCP content blocks
        text_bits = []
        content = result.get("content") if isinstance(result, dict) else None
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_bits.append(str(block.get("text", "")))
        return {
            "ok": True,
            "tool": name,
            "result": result,
            "text": "\n".join(text_bits) if text_bits else None,
        }

    # ---- PINE convenience wrappers (mcp-pine tool names) ----
    def pine_ping(self) -> dict:
        return self.call_tool("pine_ping", {})

    def pine_get_info(self) -> dict:
        return self.call_tool("pine_get_info", {})

    def pine_get_status(self) -> dict:
        return self.call_tool("pine_get_status", {})

    def pine_read32(self, address: int) -> dict:
        return self.call_tool("pine_read32", {"address": address})

    def pine_read_range(self, address: int, length: int = 64) -> dict:
        return self.call_tool("pine_read_range", {"address": address, "length": length})

    def pine_write32(self, address: int, value: int) -> dict:
        return self.call_tool("pine_write32", {"address": address, "value": value})

    def pine_save_state(self, slot: int = 0) -> dict:
        return self.call_tool("pine_save_state", {"slot": slot})

    def pine_load_state(self, slot: int = 0) -> dict:
        return self.call_tool("pine_load_state", {"slot": slot})

    def feed_emu_bridge(self, emu_bridge, session_id: str = "default", game: str = "") -> dict:
        """Pull game info + a small RAM snapshot into Lloyd emu_bridge."""
        if emu_bridge is None:
            return {"ok": False, "error": "no emu_bridge"}
        info = self.pine_get_info()
        status = self.pine_get_status()
        title = ""
        serial = ""
        if info.get("ok") and info.get("text"):
            title = info["text"][:120]
        elif info.get("result"):
            title = str(info["result"])[:120]
        gname = game or title or "mcp-pine"
        values: Dict[str, Any] = {"mcp_connected": True, "mcp_status": status.get("text") or status.get("result")}
        # sample EE RAM start (common for game data)
        rng = self.pine_read_range(0x00100000, 32)
        if rng.get("ok"):
            values["ram_sample"] = (rng.get("text") or str(rng.get("result")))[:200]
        out = emu_bridge.observe_values(session_id=session_id, values=values, game=gname)
        if title:
            try:
                emu_bridge.lloyd.remember(f"mcp pine game: {title} serial={serial}") if getattr(emu_bridge, "lloyd", None) else None
            except Exception:
                pass
        return {"ok": True, "info": info, "status": status, "values": out}

    # ---- transports ----
    def _rpc_stdio(self, method: str, params: dict) -> dict:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            return {"error": "stdio process not running"}
        msg = {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params}
        line = json.dumps(msg) + "\n"
        try:
            self._proc.stdin.write(line.encode("utf-8"))
            self._proc.stdin.flush()
        except Exception as e:
            return {"error": f"write failed: {e}"}
        deadline = time.time() + float(self.config.get("timeout_s") or 20)
        while time.time() < deadline:
            if self._proc.poll() is not None:
                err = ""
                try:
                    err = self._proc.stderr.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    pass
                return {"error": f"mcp process exited: {err or self._proc.returncode}"}
            # blocking readline with timeout via thread is heavy; use poll-style short reads
            try:
                # Many MCP servers use Content-Length framing; mcp-pine often uses newline JSON.
                raw = self._read_stdio_message(deadline)
                if raw is None:
                    continue
                data = json.loads(raw)
                if data.get("id") == msg["id"] or "result" in data or "error" in data:
                    return data
            except json.JSONDecodeError:
                continue
            except Exception as e:
                return {"error": str(e)}
        return {"error": f"timeout waiting for {method}"}

    def _notify_stdio(self, method: str, params: dict) -> None:
        if self._proc is None or self._proc.stdin is None:
            return
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        try:
            self._proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
            self._proc.stdin.flush()
        except Exception:
            pass

    def _read_stdio_message(self, deadline: float) -> Optional[str]:
        """Read one MCP message: either newline-delimited JSON or Content-Length framed."""
        assert self._proc is not None and self._proc.stdout is not None
        buf = b""
        # peek first line / headers
        while time.time() < deadline:
            chunk = self._proc.stdout.read(1)
            if not chunk:
                time.sleep(0.01)
                if self._proc.poll() is not None:
                    return None
                continue
            buf += chunk
            if buf.endswith(b"\n") and b"Content-Length" not in buf[:40]:
                return buf.decode("utf-8", errors="replace").strip()
            if b"\r\n\r\n" in buf or b"\n\n" in buf:
                # framed
                header, rest = buf.split(b"\r\n\r\n", 1) if b"\r\n\r\n" in buf else buf.split(b"\n\n", 1)
                try:
                    length = int(
                        next(
                            line.split(b":")[1].strip()
                            for line in header.split(b"\n")
                            if line.lower().startswith(b"content-length")
                        )
                    )
                except Exception:
                    return buf.decode("utf-8", errors="replace").strip()
                body = rest
                while len(body) < length and time.time() < deadline:
                    more = self._proc.stdout.read(length - len(body))
                    if not more:
                        time.sleep(0.01)
                        continue
                    body += more
                return body[:length].decode("utf-8", errors="replace")
        return None

    def _rpc_http(self, method: str, params: dict) -> dict:
        url = (self.config.get("http_url") or "").strip()
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=float(self.config.get("timeout_s") or 20)) as r:
                raw = r.read().decode("utf-8", errors="replace")
                # SSE: take last data line if needed
                if raw.lstrip().startswith("event:") or "data:" in raw[:20]:
                    for line in raw.splitlines():
                        if line.startswith("data:"):
                            raw = line[5:].strip()
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:500]
            return {"error": {"code": e.code, "message": body}}
        except Exception as e:
            return {"error": str(e)}


# singleton used by server / agent
_mcp: Optional[MCPClient] = None


def get_mcp(config: Optional[dict] = None) -> MCPClient:
    global _mcp
    if _mcp is None:
        _mcp = MCPClient(config=config)
    return _mcp
