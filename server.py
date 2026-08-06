"""
Lloyd Local + Deployable Server
===============================
  /chat /vision /audio /textfiction/* /emu/* /mcp/* /pine/* /status
  /pine = FULL PINE opcode set (pure Python)
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import sys
import os
import tempfile
import base64
import time
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).parent))

from lloyd.agent import Lloyd
from lloyd.trainer import LloydTrainer

try:
    from lloyd.text_fiction_bridge import TextFictionBridge
except ImportError:
    from text_fiction_bridge import TextFictionBridge  # type: ignore

try:
    from lloyd.emu_bridge import EmuBridge
except ImportError:
    from emu_bridge import EmuBridge  # type: ignore

try:
    from lloyd.mcp_client import get_mcp
except ImportError:
    get_mcp = None  # type: ignore

try:
    from lloyd.pine_client import get_pine
except ImportError:
    get_pine = None  # type: ignore

trainer = LloydTrainer()
lloyd = Lloyd(trainer=trainer)
tf_bridge = TextFictionBridge(lloyd=lloyd, trainer=trainer)
emu_bridge = EmuBridge(lloyd=lloyd, trainer=trainer)
lloyd.emu_bridge = emu_bridge
mcp = get_mcp() if get_mcp else None
if mcp is not None:
    lloyd.mcp = mcp
pine = get_pine() if get_pine else None
if pine is not None:
    lloyd.pine = pine

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
BRAIN_DIR = Path("brains")
BRAIN_DIR.mkdir(exist_ok=True)
VISION_DIR = Path("vision_inbox")
VISION_DIR.mkdir(exist_ok=True)


class LloydHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / "interface" / "mobile_web"), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()

        if path == "/status":
            try:
                tstat = trainer.status() if trainer else "no trainer"
                payload = {
                    "agent": "lloyd", "mode": "agent-only", "mind": "online",
                    "vision": "online", "audio": "online",
                    "textfiction": tf_bridge.status(), "emu": emu_bridge.status(),
                    "trainer": tstat,
                    "autonomy": lloyd.autonomy.status() if hasattr(lloyd, "autonomy") else "n/a",
                    "ts": time.time(),
                }
                if mcp is not None:
                    payload["mcp"] = mcp.status()
                if pine is not None:
                    payload["pine"] = pine.status_dict()
                self._json_response(payload)
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/export":
            try:
                out = BRAIN_DIR / "lloyd_export.lloyd"
                lloyd.export_brain(out, trainer=trainer)
                data = out.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", "attachment; filename=lloyd_brain.lloyd")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/textfiction/status":
            self._json_response(tf_bridge.status())
            return

        if path == "/emu/status":
            self._json_response(emu_bridge.status())
            return

        if path == "/emu/state":
            sid = (qs.get("session") or ["default"])[0]
            sess = emu_bridge.get_session(sid)
            st = sess.full_state() if hasattr(sess, "full_state") else sess.summary()
            self._json_response(st)
            return

        if path == "/emu/inputs":
            sid = (qs.get("session") or ["default"])[0]
            max_n = int((qs.get("max") or ["16"])[0])
            self._json_response(emu_bridge.drain_inputs(sid, max_n=max_n))
            return

        if path == "/mcp/status":
            self._json_response(mcp.status() if mcp else {"error": "mcp missing"})
            return

        if path == "/mcp/tools":
            if mcp is None:
                self._json_response({"error": "mcp missing"}, status=500)
            else:
                if not mcp.connected:
                    mcp.connect()
                self._json_response({"tools": mcp.list_tools()})
            return

        if path == "/pine/status":
            self._json_response(pine.status_dict() if pine else {"error": "pine missing"})
            return

        if path == "/pine/features":
            self._json_response({"features": pine.features() if pine else [], "note": "full official PINE opcode set"})
            return

        return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        path = self.path.split("?")[0]

        if path == "/chat":
            try:
                data = json.loads(body.decode()) if body else {}
                user_msg = (data.get("message") or "").strip()
                if not user_msg:
                    self._json_response({"reply": "yo say something", "agent": True})
                    return
                result = lloyd.think(user_msg)
                if isinstance(result, dict):
                    payload = {"reply": result.get("message", result.get("reply", "")), "image": result.get("image"), "id": result.get("id"), "agent": True, "mind": "direct"}
                else:
                    payload = {"reply": str(result), "agent": True, "mind": "direct"}
                self._json_response(payload)
            except Exception as e:
                self._json_response({"reply": f"error: {e}", "agent": True}, status=500)
            return

        # ---- FULL PINE ----
        if path == "/pine/connect":
            if pine is None:
                self._json_response({"error": "pine missing"}, status=500)
            else:
                try:
                    data = json.loads(body.decode()) if body else {}
                except Exception:
                    data = {}
                for k in ("slot", "host", "socket_path", "timeout_s"):
                    if data.get(k) is not None:
                        pine.config[k] = data[k]
                self._json_response(pine.connect())
            return

        if path == "/pine/disconnect":
            self._json_response(pine.disconnect() if pine else {"error": "pine missing"})
            return

        if path == "/pine/call":
            if pine is None:
                self._json_response({"error": "pine missing"}, status=500)
            else:
                try:
                    data = json.loads(body.decode()) if body else {}
                    op = data.get("op") or data.get("method") or data.get("command") or "info"
                    args = {k: v for k, v in data.items() if k not in ("op", "method", "command")}
                    self._json_response(pine.call(op, **args))
                except Exception as e:
                    self._json_response({"error": str(e)}, status=500)
            return

        if path == "/pine/sync":
            if pine is None:
                self._json_response({"error": "pine missing"}, status=500)
            else:
                try:
                    data = json.loads(body.decode()) if body else {}
                    if not pine.connected:
                        conn = pine.connect()
                        if not conn.get("ok"):
                            self._json_response(conn, status=500)
                            return
                    out = pine.sync_to_emu(emu_bridge, session_id=data.get("session") or "default")
                    self._json_response({**out, "agent": True})
                except Exception as e:
                    self._json_response({"error": str(e)}, status=500)
            return

        if path == "/mcp/connect":
            if mcp is None:
                self._json_response({"error": "mcp missing"}, status=500)
            else:
                try:
                    data = json.loads(body.decode()) if body else {}
                except Exception:
                    data = {}
                mcp.config["enabled"] = True
                if data.get("command"):
                    mcp.config["command"] = data["command"]
                if data.get("args"):
                    mcp.config["args"] = data["args"]
                if data.get("http_url"):
                    mcp.config["http_url"] = data["http_url"]
                    mcp.config["transport"] = "http"
                if data.get("env"):
                    mcp.config.setdefault("env", {}).update(data["env"])
                self._json_response(mcp.connect())
            return

        if path == "/mcp/disconnect":
            self._json_response(mcp.disconnect() if mcp else {"error": "mcp missing"})
            return

        if path == "/mcp/call":
            if mcp is None:
                self._json_response({"error": "mcp missing"}, status=500)
            else:
                try:
                    data = json.loads(body.decode()) if body else {}
                    name = data.get("name") or data.get("tool") or ""
                    arguments = data.get("arguments") or data.get("args") or {}
                    if not name:
                        self._json_response({"error": "missing tool name"}, status=400)
                        return
                    self._json_response(mcp.call_tool(name, arguments))
                except Exception as e:
                    self._json_response({"error": str(e)}, status=500)
            return

        if path == "/mcp/sync":
            if mcp is None:
                self._json_response({"error": "mcp missing"}, status=500)
            else:
                try:
                    data = json.loads(body.decode()) if body else {}
                    if not mcp.connected:
                        mcp.config["enabled"] = True
                        conn = mcp.connect()
                        if not conn.get("ok"):
                            self._json_response(conn, status=500)
                            return
                    out = mcp.feed_emu_bridge(emu_bridge, session_id=data.get("session") or "default", game=data.get("game") or "")
                    self._json_response({**out, "agent": True})
                except Exception as e:
                    self._json_response({"error": str(e)}, status=500)
            return

        if path == "/vision":
            try:
                data = json.loads(body.decode()) if body else {}
                caption = (data.get("caption") or data.get("prompt") or "scene").strip()
                b64 = data.get("image_b64") or data.get("image") or ""
                learn = bool(data.get("learn", True))
                saved = None
                if b64:
                    if "," in b64:
                        b64 = b64.split(",", 1)[1]
                    raw = base64.b64decode(b64)
                    saved = VISION_DIR / f"vision_{int(time.time())}.bin"
                    saved.write_bytes(raw)
                note = f"vision seen: {caption}"
                if saved:
                    note += f" | file={saved.name}"
                lloyd.remember(note)
                agent_reply = lloyd.think(f"you just saw: {caption}. react briefly.")
                if isinstance(agent_reply, dict):
                    agent_reply = agent_reply.get("message") or agent_reply.get("reply") or ""
                if learn and trainer is not None:
                    try:
                        trainer.train_on_text(note + " " + str(agent_reply), steps=6, lr=0.008)
                    except Exception:
                        pass
                self._json_response({"ok": True, "vision": True, "caption": caption, "reply": str(agent_reply)[:400], "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/audio":
            try:
                data = json.loads(body.decode()) if body else {}
                transcript = (data.get("transcript") or data.get("text") or data.get("message") or "").strip()
                if not transcript:
                    self._json_response({"reply": "no transcript", "audio": True})
                    return
                lloyd.remember(f"audio heard: {transcript[:500]}")
                result = lloyd.think(transcript)
                reply = result.get("message") or result.get("reply") if isinstance(result, dict) else str(result)
                self._json_response({"reply": reply, "audio": True, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/textfiction/observe":
            try:
                data = json.loads(body.decode()) if body else {}
                out = tf_bridge.observe(room_text=data.get("room_text") or data.get("room") or "", choices=data.get("choices") or [], command=data.get("command") or data.get("player") or "", session_id=data.get("session_id") or "default", meta=data.get("meta"))
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/textfiction/suggest":
            try:
                data = json.loads(body.decode()) if body else {}
                sid = data.get("session_id") or "default"
                if data.get("room_text") or data.get("room"):
                    tf_bridge.observe(room_text=data.get("room_text") or data.get("room") or "", choices=data.get("choices") or [], session_id=sid)
                out = tf_bridge.suggest_command(sid)
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/textfiction/learn":
            try:
                data = json.loads(body.decode()) if body else {}
                out = tf_bridge.learn(data.get("session_id") or "default", steps=int(data.get("steps", 20)))
                try:
                    trainer.save_brain(BRAIN_DIR / "latest_brain.npz")
                    lloyd.memory.save(str(BRAIN_DIR / "latest_memory.json"))
                except Exception:
                    pass
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        # emu routes (full agent loop)
        if path == "/emu/tick":
            try:
                data = json.loads(body.decode()) if body else {}
                out = emu_bridge.tick(session_id=data.get("session") or data.get("session_id") or "default", game=data.get("game") or "", frame=data.get("frame"), audio=data.get("audio"), values=data.get("values"), mem=data.get("mem"), action=data.get("action"), reaction=data.get("reaction"), t_game=float(data.get("t_game") or 0), note=data.get("note") or "")
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/values":
            try:
                data = json.loads(body.decode()) if body else {}
                vals = data.get("values")
                if vals is None:
                    vals = {k: v for k, v in data.items() if k not in ("session", "session_id", "game")}
                out = emu_bridge.observe_values(session_id=data.get("session") or "default", values=vals, game=data.get("game") or "")
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/memread":
            try:
                data = json.loads(body.decode()) if body else {}
                out = emu_bridge.observe_mem(session_id=data.get("session") or "default", reads=data.get("reads"), blob_b64=data.get("blob_b64") or "", base_addr=str(data.get("base_addr") or ""))
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/rules":
            try:
                data = json.loads(body.decode()) if body else {}
                out = emu_bridge.load_rules(session_id=data.get("session") or "default", rules=data.get("rules") or data, path=data.get("path") or "", game=data.get("game") or "")
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/reaction":
            try:
                data = json.loads(body.decode()) if body else {}
                reac = data.get("reaction") or {k: v for k, v in data.items() if k not in ("session", "session_id", "game")}
                out = emu_bridge.observe_reaction(session_id=data.get("session") or "default", reaction=reac, game=data.get("game") or "")
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/frame":
            try:
                data = json.loads(body.decode()) if body else {}
                out = emu_bridge.observe_vision(session_id=data.get("session") or "default", game=data.get("game") or "", image_b64=data.get("image_b64") or data.get("image") or "", width=int(data.get("width") or 0), height=int(data.get("height") or 0), caption=data.get("caption") or data.get("note") or "", fmt=data.get("fmt") or "jpeg")
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/audio":
            try:
                data = json.loads(body.decode()) if body else {}
                out = emu_bridge.observe_audio(session_id=data.get("session") or "default", transcript=data.get("transcript") or data.get("text") or "", level=float(data.get("level") or 0), note=data.get("note") or "", pcm_b64=data.get("pcm_b64") or "")
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/action":
            try:
                data = json.loads(body.decode()) if body else {}
                out = emu_bridge.act(session_id=data.get("session") or "default", buttons=data.get("buttons") or [], sticks=data.get("sticks") or {}, hold_ms=int(data.get("hold_ms") or 50), text=data.get("text") or data.get("reason") or "")
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/decide":
            try:
                data = json.loads(body.decode()) if body else {}
                self._json_response({**emu_bridge.decide(session_id=data.get("session") or "default", goal=data.get("goal") or ""), "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/play":
            try:
                data = json.loads(body.decode()) if body else {}
                self._json_response({**emu_bridge.play_step(session_id=data.get("session") or "default", goal=data.get("goal") or ""), "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/learn":
            try:
                data = json.loads(body.decode()) if body else {}
                out = emu_bridge.learn(session_id=data.get("session") or "default", steps=int(data.get("steps") or 24))
                try:
                    trainer.save_brain(BRAIN_DIR / "latest_brain.npz")
                    lloyd.memory.save(str(BRAIN_DIR / "latest_memory.json"))
                except Exception:
                    pass
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/upload":
            try:
                content_type = self.headers.get("Content-Type", "")
                if "multipart/form-data" not in content_type:
                    self._json_response({"error": "expected multipart"}, status=400)
                    return
                body_str = body.decode("utf-8", errors="ignore")
                if "filename=" in body_str:
                    fname = f"train_{len(list(UPLOAD_DIR.glob('*')))}.txt"
                    fpath = UPLOAD_DIR / fname
                    parts = body_str.split("\r\n\r\n", 1)
                    if len(parts) > 1:
                        text = parts[1].split("\r\n--")[0]
                        fpath.write_text(text, encoding="utf-8")
                        lloyd.remember(f"User uploaded training file: {fname}")
                        self._json_response({"status": "ok", "filename": fname})
                        return
                self._json_response({"error": "could not parse file"}, status=400)
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/train":
            try:
                files = list(UPLOAD_DIR.glob("*.txt"))
                if not files:
                    self._json_response({"message": "no files uploaded yet"})
                    return
                result = trainer.train_on_files(files, steps_per_file=40)
                trainer.save_brain(BRAIN_DIR / "latest_brain.npz")
                lloyd.memory.save(str(BRAIN_DIR / "latest_memory.json"))
                self._json_response({"message": result.get("message", "trained")})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/train_images":
            try:
                data = json.loads(body.decode()) if body else {}
                result = lloyd.image_gen.train_pattern_images(epochs=int(data.get("epochs", 40)), n_images=int(data.get("n_images", 100)))
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/import":
            try:
                with tempfile.NamedTemporaryFile(suffix=".lloyd", delete=False) as tmp:
                    tmp.write(body)
                    tmp_path = tmp.name
                msg = lloyd.import_brain(tmp_path, trainer=trainer)
                os.unlink(tmp_path)
                self._json_response({"message": msg})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        self.send_error(404)

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


def run():
    port = int(os.environ.get("PORT", 8080))
    latest = BRAIN_DIR / "latest_brain.npz"
    if latest.exists():
        try:
            trainer.load_brain(latest)
            print("Restored previous neural brain")
        except Exception as e:
            print(f"Could not restore brain: {e}")
    mem = BRAIN_DIR / "latest_memory.json"
    if mem.exists():
        try:
            lloyd.memory.load(str(mem))
        except Exception:
            pass
    if pine is not None:
        try:
            print("PINE:", pine.connect())
        except Exception as e:
            print("PINE auto-connect:", e)
    if mcp is not None and mcp.enabled():
        try:
            print("MCP:", mcp.connect())
        except Exception as e:
            print("MCP:", e)
    server = HTTPServer(("0.0.0.0", port), LloydHandler)
    print(f"Lloyd live on port {port}")
    print("PINE full IPC: /pine/connect /pine/call /pine/sync /pine/features")
    print("MCP optional: /mcp/* | agent loop: /emu/*")
    server.serve_forever()


if __name__ == "__main__":
    run()
