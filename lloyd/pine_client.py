"""
Lloyd pure-Python PINE client — FULL PCSX2 / ARMSX2 IPC surface.

Every official PINE opcode:
  MsgRead8/16/32/64, MsgWrite8/16/32/64,
  MsgVersion, MsgSaveState, MsgLoadState,
  MsgTitle, MsgID, MsgUUID, MsgGameVersion, MsgStatus

Plus bulk read/write helpers (loop of MsgRead8 / MsgWrite8).

Wire format (little-endian):
  request:  [u32 total_size][payload...]
  payload commands chained; single-cmd examples:
    ReadN:  opcode(1) + addr(u32)
    WriteN: opcode(1) + addr(u32) + value
    Save/Load: opcode(1) + slot(u8)
    Version/Title/ID/UUID/GameVersion/Status: opcode(1) only
  reply: [u32 size][IPC_OK|FAIL][data...]

TCP: 127.0.0.1:slot (Windows default 28011)
Unix: $XDG_RUNTIME_DIR/pcsx2.sock.<slot> or /tmp/pcsx2.sock.<slot>
"""
from __future__ import annotations

import json
import os
import socket
import struct
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# opcodes
MsgRead8 = 0
MsgRead16 = 1
MsgRead32 = 2
MsgRead64 = 3
MsgWrite8 = 4
MsgWrite16 = 5
MsgWrite32 = 6
MsgWrite64 = 7
MsgVersion = 8
MsgSaveState = 9
MsgLoadState = 0xA
MsgTitle = 0xB
MsgID = 0xC
MsgUUID = 0xD
MsgGameVersion = 0xE
MsgStatus = 0xF

IPC_OK = 0
IPC_FAIL = 0xFF

STATUS_NAMES = {0: "Running", 1: "Paused", 2: "Shutdown"}

FEATURES = [
    "read8", "read16", "read32", "read64",
    "write8", "write16", "write32", "write64",
    "read_bytes", "write_bytes",
    "version", "title", "game_id", "uuid", "game_version", "status",
    "save_state", "load_state",
    "full_info", "sync_to_emu",
]


def _load_pine_config() -> dict:
    cfg: Dict[str, Any] = {
        "enabled": True,
        "slot": 28011,
        "host": "127.0.0.1",
        "socket_path": "",
        "prefer_unix": True,
        "timeout_s": 5.0,
    }
    for name in ("secrets.json", "mcp.json", "pine.json"):
        p = Path(name)
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        block = data.get("pine") or {}
        if isinstance(block, dict):
            cfg.update({k: v for k, v in block.items() if v is not None})
        # share MCP env defaults
        env = (data.get("mcp") or {}).get("env") or {}
        if env.get("PINE_SLOT"):
            try:
                cfg["slot"] = int(env["PINE_SLOT"])
            except Exception:
                pass
        if env.get("PINE_HOST"):
            cfg["host"] = env["PINE_HOST"]
        if env.get("PINE_SOCKET_PATH"):
            cfg["socket_path"] = env["PINE_SOCKET_PATH"]
    if os.environ.get("PINE_SLOT"):
        cfg["slot"] = int(os.environ["PINE_SLOT"])
    if os.environ.get("PINE_HOST"):
        cfg["host"] = os.environ["PINE_HOST"]
    if os.environ.get("PINE_SOCKET_PATH"):
        cfg["socket_path"] = os.environ["PINE_SOCKET_PATH"]
    if os.environ.get("LLOYD_PINE_DISABLED", "").lower() in ("1", "true"):
        cfg["enabled"] = False
    return cfg


class PineClient:
    """Full PINE IPC client — every official opcode."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or _load_pine_config()
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self.last_error = ""
        self.connected = False
        self.transport = ""

    def features(self) -> List[str]:
        return list(FEATURES)

    def status_dict(self) -> dict:
        return {
            "enabled": bool(self.config.get("enabled", True)),
            "connected": self.connected,
            "transport": self.transport,
            "slot": self.config.get("slot"),
            "host": self.config.get("host"),
            "socket_path": self.config.get("socket_path") or None,
            "features": self.features(),
            "feature_count": len(FEATURES),
            "last_error": self.last_error or None,
            "protocol": "PINE (full official opcode set)",
        }

    def connect(self) -> dict:
        if not self.config.get("enabled", True):
            return {"ok": False, "error": "pine disabled"}
        with self._lock:
            self.disconnect()
            slot = int(self.config.get("slot") or 28011)
            host = self.config.get("host") or "127.0.0.1"
            sock_path = (self.config.get("socket_path") or "").strip()
            prefer_unix = bool(self.config.get("prefer_unix", True))
            timeout = float(self.config.get("timeout_s") or 5)

            errors = []
            # Unix first on non-Windows
            if prefer_unix and os.name != "nt":
                paths = []
                if sock_path:
                    paths.append(sock_path)
                runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
                paths += [
                    f"{runtime}/pcsx2.sock.{slot}",
                    f"/tmp/pcsx2.sock.{slot}",
                    f"{runtime}/pcsx2.sock",
                    f"/tmp/pcsx2.sock",
                    f"{runtime}/armsx2.sock.{slot}",
                    f"/tmp/armsx2.sock.{slot}",
                ]
                for path in paths:
                    if not path:
                        continue
                    try:
                        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        s.settimeout(timeout)
                        s.connect(path)
                        self._sock = s
                        self.connected = True
                        self.transport = f"unix:{path}"
                        self.last_error = ""
                        return {"ok": True, "transport": self.transport, "features": FEATURES}
                    except Exception as e:
                        errors.append(f"unix {path}: {e}")
                        try:
                            s.close()
                        except Exception:
                            pass

            # TCP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((host, slot))
                self._sock = s
                self.connected = True
                self.transport = f"tcp:{host}:{slot}"
                self.last_error = ""
                return {"ok": True, "transport": self.transport, "features": FEATURES}
            except Exception as e:
                errors.append(f"tcp {host}:{slot}: {e}")
                try:
                    s.close()
                except Exception:
                    pass

            self.last_error = " | ".join(errors)[:500]
            self.connected = False
            return {"ok": False, "error": self.last_error}

    def disconnect(self) -> dict:
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
        self._sock = None
        self.connected = False
        self.transport = ""
        return {"ok": True}

    def _ensure(self) -> None:
        if not self.connected or self._sock is None:
            out = self.connect()
            if not out.get("ok"):
                raise RuntimeError(out.get("error") or "pine connect failed")

    def _transact(self, payload: bytes) -> bytes:
        self._ensure()
        assert self._sock is not None
        # header: total message size including the 4-byte size field
        total = 4 + len(payload)
        packet = struct.pack("<I", total) + payload
        with self._lock:
            self._sock.sendall(packet)
            # read reply size
            hdr = self._recv_exact(4)
            (reply_size,) = struct.unpack("<I", hdr)
            if reply_size < 5:
                raise RuntimeError(f"bad reply size {reply_size}")
            body = self._recv_exact(reply_size - 4)
        return body

    def _recv_exact(self, n: int) -> bytes:
        assert self._sock is not None
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise RuntimeError("connection closed")
            buf += chunk
        return buf

    def _check_ok(self, body: bytes) -> bytes:
        if not body:
            raise RuntimeError("empty reply")
        if body[0] == IPC_FAIL:
            raise RuntimeError("PINE FAIL (no game / bad addr / rejected)")
        if body[0] != IPC_OK:
            raise RuntimeError(f"unknown reply tag {body[0]:#x}")
        return body[1:]

    # ---- reads ----
    def read8(self, addr: int) -> int:
        data = self._check_ok(self._transact(bytes([MsgRead8]) + struct.pack("<I", addr & 0xFFFFFFFF)))
        return data[0]

    def read16(self, addr: int) -> int:
        data = self._check_ok(self._transact(bytes([MsgRead16]) + struct.pack("<I", addr & 0xFFFFFFFF)))
        return struct.unpack("<H", data[:2])[0]

    def read32(self, addr: int) -> int:
        data = self._check_ok(self._transact(bytes([MsgRead32]) + struct.pack("<I", addr & 0xFFFFFFFF)))
        return struct.unpack("<I", data[:4])[0]

    def read64(self, addr: int) -> int:
        data = self._check_ok(self._transact(bytes([MsgRead64]) + struct.pack("<I", addr & 0xFFFFFFFF)))
        return struct.unpack("<Q", data[:8])[0]

    def read_bytes(self, addr: int, length: int) -> bytes:
        length = max(0, min(int(length), 4096))
        out = bytearray()
        for i in range(length):
            out.append(self.read8((addr + i) & 0xFFFFFFFF))
        return bytes(out)

    # ---- writes ----
    def write8(self, addr: int, value: int) -> None:
        self._check_ok(
            self._transact(
                bytes([MsgWrite8]) + struct.pack("<I", addr & 0xFFFFFFFF) + bytes([value & 0xFF])
            )
        )

    def write16(self, addr: int, value: int) -> None:
        self._check_ok(
            self._transact(
                bytes([MsgWrite16])
                + struct.pack("<I", addr & 0xFFFFFFFF)
                + struct.pack("<H", value & 0xFFFF)
            )
        )

    def write32(self, addr: int, value: int) -> None:
        self._check_ok(
            self._transact(
                bytes([MsgWrite32])
                + struct.pack("<I", addr & 0xFFFFFFFF)
                + struct.pack("<I", value & 0xFFFFFFFF)
            )
        )

    def write64(self, addr: int, value: int) -> None:
        self._check_ok(
            self._transact(
                bytes([MsgWrite64])
                + struct.pack("<I", addr & 0xFFFFFFFF)
                + struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)
            )
        )

    def write_bytes(self, addr: int, data: bytes) -> None:
        data = data[:4096]
        for i, b in enumerate(data):
            self.write8((addr + i) & 0xFFFFFFFF, b)

    # ---- meta ----
    def _read_string_cmd(self, opcode: int) -> str:
        data = self._check_ok(self._transact(bytes([opcode])))
        # length-prefixed or null-terminated depending on server; try both
        if len(data) >= 4:
            # some builds: first byte is length of zstring including null
            try:
                # C-string after optional length byte
                if data[0] < len(data) and data[0] > 0:
                    n = data[0]
                    chunk = data[1 : 1 + n]
                    return chunk.split(b"\x00")[0].decode("utf-8", errors="replace")
            except Exception:
                pass
        return data.split(b"\x00")[0].decode("utf-8", errors="replace")

    def version(self) -> str:
        return self._read_string_cmd(MsgVersion)

    def title(self) -> str:
        return self._read_string_cmd(MsgTitle)

    def game_id(self) -> str:
        return self._read_string_cmd(MsgID)

    def uuid(self) -> str:
        return self._read_string_cmd(MsgUUID)

    def game_version(self) -> str:
        return self._read_string_cmd(MsgGameVersion)

    def emu_status(self) -> dict:
        data = self._check_ok(self._transact(bytes([MsgStatus])))
        code = struct.unpack("<I", data[:4])[0] if len(data) >= 4 else data[0]
        return {"code": code, "name": STATUS_NAMES.get(code, f"unknown({code})")}

    def save_state(self, slot: int = 0) -> None:
        self._check_ok(self._transact(bytes([MsgSaveState, slot & 0xFF])))

    def load_state(self, slot: int = 0) -> None:
        self._check_ok(self._transact(bytes([MsgLoadState, slot & 0xFF])))

    def full_info(self) -> dict:
        out: Dict[str, Any] = {"ok": True, "transport": self.transport}
        for key, fn in (
            ("version", self.version),
            ("title", self.title),
            ("game_id", self.game_id),
            ("uuid", self.uuid),
            ("game_version", self.game_version),
        ):
            try:
                out[key] = fn()
            except Exception as e:
                out[key] = None
                out[f"{key}_error"] = str(e)
        try:
            out["status"] = self.emu_status()
        except Exception as e:
            out["status"] = {"error": str(e)}
        return out

    def call(self, op: str, **kwargs) -> dict:
        """Unified dispatcher for HTTP / chat."""
        op = (op or "").lower().strip()
        try:
            if op in ("connect",):
                return self.connect()
            if op in ("disconnect",):
                return self.disconnect()
            if op in ("features", "caps", "capabilities"):
                return {"ok": True, "features": FEATURES}
            if op in ("info", "full_info"):
                return self.full_info()
            if op in ("version",):
                return {"ok": True, "version": self.version()}
            if op in ("title",):
                return {"ok": True, "title": self.title()}
            if op in ("game_id", "id", "serial"):
                return {"ok": True, "game_id": self.game_id()}
            if op in ("uuid",):
                return {"ok": True, "uuid": self.uuid()}
            if op in ("game_version",):
                return {"ok": True, "game_version": self.game_version()}
            if op in ("status", "emu_status"):
                return {"ok": True, **self.emu_status()}
            if op in ("save", "save_state"):
                self.save_state(int(kwargs.get("slot", 0)))
                return {"ok": True, "saved_slot": int(kwargs.get("slot", 0))}
            if op in ("load", "load_state"):
                self.load_state(int(kwargs.get("slot", 0)))
                return {"ok": True, "loaded_slot": int(kwargs.get("slot", 0))}
            addr = kwargs.get("address", kwargs.get("addr", 0))
            if isinstance(addr, str):
                addr = int(addr, 0)
            if op == "read8":
                return {"ok": True, "value": self.read8(int(addr))}
            if op == "read16":
                return {"ok": True, "value": self.read16(int(addr))}
            if op == "read32":
                return {"ok": True, "value": self.read32(int(addr))}
            if op == "read64":
                return {"ok": True, "value": self.read64(int(addr))}
            if op in ("read_bytes", "read_range"):
                length = int(kwargs.get("length", kwargs.get("size", 64)))
                data = self.read_bytes(int(addr), length)
                return {"ok": True, "hex": data.hex(), "length": len(data)}
            val = kwargs.get("value", 0)
            if isinstance(val, str):
                val = int(val, 0)
            if op == "write8":
                self.write8(int(addr), int(val))
                return {"ok": True}
            if op == "write16":
                self.write16(int(addr), int(val))
                return {"ok": True}
            if op == "write32":
                self.write32(int(addr), int(val))
                return {"ok": True}
            if op == "write64":
                self.write64(int(addr), int(val))
                return {"ok": True}
            if op in ("write_bytes",):
                hx = kwargs.get("hex") or kwargs.get("data") or ""
                self.write_bytes(int(addr), bytes.fromhex(hx.replace(" ", "")))
                return {"ok": True}
            return {"ok": False, "error": f"unknown op {op}", "features": FEATURES}
        except Exception as e:
            self.last_error = str(e)
            return {"ok": False, "error": str(e), "op": op}

    def sync_to_emu(self, emu_bridge, session_id: str = "default") -> dict:
        if emu_bridge is None:
            return {"ok": False, "error": "no emu_bridge"}
        info = self.full_info()
        title = info.get("title") or "pine"
        values: Dict[str, Any] = {
            "pine": True,
            "game_id": info.get("game_id"),
            "uuid": info.get("uuid"),
            "emu_status": (info.get("status") or {}).get("name"),
            "version": info.get("version"),
        }
        try:
            sample = self.read_bytes(0x00100000, 32)
            values["ram_00100000"] = sample.hex()
        except Exception as e:
            values["ram_error"] = str(e)
        out = emu_bridge.observe_values(session_id=session_id, values=values, game=str(title)[:80])
        try:
            if getattr(emu_bridge, "lloyd", None):
                emu_bridge.lloyd.remember(
                    f"pine sync: {title} id={info.get('game_id')} status={values.get('emu_status')}"
                )
        except Exception:
            pass
        return {"ok": True, "info": info, "values": out}


_pine: Optional[PineClient] = None


def get_pine(config: Optional[dict] = None) -> PineClient:
    global _pine
    if _pine is None:
        _pine = PineClient(config=config)
    return _pine
