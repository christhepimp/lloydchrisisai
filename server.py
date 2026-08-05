"""
Lloyd Local + Deployable Server
===============================
Full agent mind connection:
  /chat          — agent think (straight to mind)
  /vision        — image → memory + optional pattern learn
  /audio         — transcript / audio note → think
  /textfiction/* — play + learn from Text Fiction APK sessions
  /emu/*         — ARMSX2 / PS2: vision, audio, controller actions, agent play/learn
  /status        — agent health
  /upload /train /train_images /export /import — existing
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

trainer = LloydTrainer()
lloyd = Lloyd(trainer=trainer)
tf_bridge = TextFictionBridge(lloyd=lloyd, trainer=trainer)
emu_bridge = EmuBridge(lloyd=lloyd, trainer=trainer)

# Let agent reach the emu bridge for chat commands
lloyd.emu_bridge = emu_bridge

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
BRAIN_DIR = Path("brains")
BRAIN_DIR.mkdir(exist_ok=True)
VISION_DIR = Path("vision_inbox")
VISION_DIR.mkdir(exist_ok=True)


class LloydHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(Path(__file__).parent / "interface" / "mobile_web"),
            **kwargs,
        )

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
                    "agent": "lloyd",
                    "mode": "agent-only",
                    "mind": "online",
                    "vision": "online",
                    "audio": "online",
                    "textfiction": tf_bridge.status(),
                    "emu": emu_bridge.status(),
                    "trainer": tstat,
                    "autonomy": lloyd.autonomy.status() if hasattr(lloyd, "autonomy") else "n/a",
                    "ts": time.time(),
                }
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
                self.send_header(
                    "Content-Disposition", "attachment; filename=lloyd_brain.lloyd"
                )
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

        # ---- ARMSX2 / PS2 emu API ----
        if path == "/emu/status":
            self._json_response(emu_bridge.status())
            return

        if path == "/emu/state":
            sid = (qs.get("session") or ["default"])[0]
            sess = emu_bridge.get_session(sid)
            self._json_response(sess.summary())
            return

        if path == "/emu/inputs":
            sid = (qs.get("session") or ["default"])[0]
            max_n = int((qs.get("max") or ["16"])[0])
            self._json_response(emu_bridge.drain_inputs(sid, max_n=max_n))
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
                    payload = {
                        "reply": result.get("message", result.get("reply", "")),
                        "image": result.get("image"),
                        "id": result.get("id"),
                        "agent": True,
                        "mind": "direct",
                    }
                else:
                    payload = {"reply": str(result), "agent": True, "mind": "direct"}
                self._json_response(payload)
            except Exception as e:
                self._json_response({"reply": f"error: {e}", "agent": True}, status=500)
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
                    note += f" | file={saved.name} bytes={saved.stat().st_size}"
                lloyd.remember(note)
                reply_bits = [note]
                agent_reply = lloyd.think(
                    f"you just saw an image described as: {caption}. react briefly as agent."
                )
                if isinstance(agent_reply, dict):
                    agent_reply = agent_reply.get("message") or agent_reply.get("reply") or ""
                reply_bits.append(str(agent_reply)[:400])
                if learn and trainer is not None:
                    try:
                        trainer.train_on_text(note + " " + str(agent_reply), steps=6, lr=0.008)
                        reply_bits.append("vision trained")
                    except Exception:
                        pass
                self._json_response({
                    "ok": True,
                    "vision": True,
                    "caption": caption,
                    "saved": str(saved) if saved else None,
                    "reply": " | ".join(reply_bits),
                    "agent": True,
                })
            except Exception as e:
                self._json_response({"error": str(e), "vision": True}, status=500)
            return

        if path == "/audio":
            try:
                data = json.loads(body.decode()) if body else {}
                transcript = (
                    data.get("transcript") or data.get("text") or data.get("message") or ""
                ).strip()
                meta = data.get("meta") or {}
                if not transcript:
                    self._json_response({
                        "reply": "no transcript — send speech-to-text text",
                        "audio": True,
                    })
                    return
                lloyd.remember(f"audio heard: {transcript[:500]}")
                result = lloyd.think(transcript)
                if isinstance(result, dict):
                    reply = result.get("message") or result.get("reply") or ""
                    image = result.get("image")
                else:
                    reply = str(result)
                    image = None
                self._json_response({
                    "reply": reply,
                    "image": image,
                    "audio": True,
                    "transcript": transcript[:300],
                    "meta": meta,
                    "agent": True,
                    "mind": "direct",
                })
            except Exception as e:
                self._json_response({"error": str(e), "audio": True}, status=500)
            return

        if path == "/textfiction/observe":
            try:
                data = json.loads(body.decode()) if body else {}
                out = tf_bridge.observe(
                    room_text=data.get("room_text") or data.get("room") or "",
                    choices=data.get("choices") or [],
                    command=data.get("command") or data.get("player") or "",
                    session_id=data.get("session_id") or "default",
                    meta=data.get("meta"),
                )
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/textfiction/suggest":
            try:
                data = json.loads(body.decode()) if body else {}
                sid = data.get("session_id") or "default"
                if data.get("room_text") or data.get("room"):
                    tf_bridge.observe(
                        room_text=data.get("room_text") or data.get("room") or "",
                        choices=data.get("choices") or [],
                        session_id=sid,
                    )
                out = tf_bridge.suggest_command(sid)
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/textfiction/learn":
            try:
                data = json.loads(body.decode()) if body else {}
                sid = data.get("session_id") or "default"
                steps = int(data.get("steps", 20))
                out = tf_bridge.learn(sid, steps=steps)
                try:
                    trainer.save_brain(BRAIN_DIR / "latest_brain.npz")
                    lloyd.memory.save(str(BRAIN_DIR / "latest_memory.json"))
                except Exception:
                    pass
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        # ---- ARMSX2 / PS2 emu API ----
        if path == "/emu/frame":
            try:
                data = json.loads(body.decode()) if body else {}
                sid = data.get("session") or data.get("session_id") or "default"
                out = emu_bridge.observe_vision(
                    session_id=sid,
                    game=data.get("game") or "",
                    image_b64=data.get("image_b64") or data.get("image") or "",
                    width=int(data.get("width") or 0),
                    height=int(data.get("height") or 0),
                    caption=data.get("caption") or data.get("note") or "",
                    fmt=data.get("fmt") or "jpeg",
                )
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/audio":
            try:
                data = json.loads(body.decode()) if body else {}
                sid = data.get("session") or data.get("session_id") or "default"
                out = emu_bridge.observe_audio(
                    session_id=sid,
                    transcript=data.get("transcript") or data.get("text") or "",
                    level=float(data.get("level") or 0),
                    note=data.get("note") or "",
                    pcm_b64=data.get("pcm_b64") or "",
                )
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/action":
            try:
                data = json.loads(body.decode()) if body else {}
                sid = data.get("session") or data.get("session_id") or "default"
                out = emu_bridge.act(
                    session_id=sid,
                    buttons=data.get("buttons") or [],
                    sticks=data.get("sticks") or {},
                    hold_ms=int(data.get("hold_ms") or 50),
                    text=data.get("text") or data.get("reason") or "",
                )
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/decide":
            try:
                data = json.loads(body.decode()) if body else {}
                sid = data.get("session") or data.get("session_id") or "default"
                goal = data.get("goal") or ""
                out = emu_bridge.decide(session_id=sid, goal=goal)
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/play":
            try:
                data = json.loads(body.decode()) if body else {}
                sid = data.get("session") or data.get("session_id") or "default"
                goal = data.get("goal") or ""
                out = emu_bridge.play_step(session_id=sid, goal=goal)
                self._json_response({**out, "agent": True})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/emu/learn":
            try:
                data = json.loads(body.decode()) if body else {}
                sid = data.get("session") or data.get("session_id") or "default"
                steps = int(data.get("steps") or 24)
                out = emu_bridge.learn(session_id=sid, steps=steps)
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
                        self._json_response({
                            "status": "ok",
                            "filename": fname,
                            "message": f"got it. saved as {fname}. hit Train when ready.",
                        })
                        return
                self._json_response({"error": "could not parse file"}, status=400)
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/train":
            try:
                files = list(UPLOAD_DIR.glob("*.txt"))
                if not files:
                    self._json_response({"message": "no files uploaded yet. upload a .txt first."})
                    return
                result = trainer.train_on_files(files, steps_per_file=40)
                for f in files:
                    text = f.read_text(encoding="utf-8", errors="ignore")[:300]
                    lloyd.remember(f"Trained on {f.name}: {text}")
                trainer.save_brain(BRAIN_DIR / "latest_brain.npz")
                lloyd.memory.save(str(BRAIN_DIR / "latest_memory.json"))
                try:
                    lloyd.image_gen.save(BRAIN_DIR / "latest_image_net.npz")
                except Exception:
                    pass
                self._json_response({
                    "message": result["message"] + " " + " | ".join(result.get("reports", [])[:3])
                })
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        if path == "/train_images":
            try:
                data = {}
                if body:
                    try:
                        data = json.loads(body.decode())
                    except Exception:
                        data = {}
                epochs = int(data.get("epochs", 40))
                n_images = int(data.get("n_images", 100))
                result = lloyd.image_gen.train_pattern_images(epochs=epochs, n_images=n_images)
                if "error" in result:
                    self._json_response(result, status=500)
                    return
                try:
                    lloyd.image_gen.save(BRAIN_DIR / "latest_image_net.npz")
                except Exception:
                    pass
                self._json_response({
                    "message": result.get(
                        "message",
                        f"trained {epochs} epochs on {n_images} hardcoded pixel arrays",
                    ),
                    **{k: v for k, v in result.items() if k != "message"},
                })
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
            print("Restored previous memory")
        except Exception:
            pass
    img_net = BRAIN_DIR / "latest_image_net.npz"
    if img_net.exists():
        try:
            lloyd.image_gen.load(img_net)
            print("Restored previous image net")
        except Exception:
            pass

    server = HTTPServer(("0.0.0.0", port), LloydHandler)
    print(f"Lloyd agent mind live on port {port}")
    print("Endpoints: /chat /vision /audio /emu/* /textfiction/* /status /export ...")
    print("ARMSX2 bridge: POST /emu/frame /emu/audio /emu/action /emu/decide /emu/play /emu/learn")
    server.serve_forever()


if __name__ == "__main__":
    run()
