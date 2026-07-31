"""
Lloyd Local + Deployable Server
===============================
Works on localhost and cloud hosts.
Same original brain: pure-NumPy chat + pure-NumPy images.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import sys
import os
import tempfile

sys.path.insert(0, str(Path(__file__).parent))

from lloyd.agent import Lloyd
from lloyd.trainer import LloydTrainer

trainer = LloydTrainer()
lloyd = Lloyd(trainer=trainer)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
BRAIN_DIR = Path("brains")
BRAIN_DIR.mkdir(exist_ok=True)


class LloydHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(Path(__file__).parent / "interface" / "mobile_web"),
            **kwargs,
        )

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()

        if self.path == "/export":
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

        return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if self.path == "/chat":
            try:
                data = json.loads(body.decode())
                user_msg = data.get("message", "").strip()
                if not user_msg:
                    self._json_response({"reply": "yo say something"})
                    return
                result = lloyd.think(user_msg)
                if isinstance(result, dict):
                    payload = {
                        "reply": result.get("message", ""),
                        "image": result.get("image"),
                        "id": result.get("id"),
                    }
                else:
                    payload = {"reply": result}
                self._json_response(payload)
            except Exception as e:
                self._json_response({"reply": f"error: {e}"}, status=500)

        elif self.path == "/upload":
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
                        self._json_response(
                            {
                                "status": "ok",
                                "filename": fname,
                                "message": f"got it. saved as {fname}. hit Train when ready.",
                            }
                        )
                        return
                self._json_response({"error": "could not parse file"}, status=400)
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)

        elif self.path == "/train":
            try:
                files = list(UPLOAD_DIR.glob("*.txt"))
                if not files:
                    self._json_response(
                        {"message": "no files uploaded yet. upload a .txt first."}
                    )
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

                self._json_response(
                    {
                        "message": result["message"]
                        + " "
                        + " | ".join(result.get("reports", [])[:3])
                    }
                )
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)

        elif self.path == "/train_images":
            try:
                data = {}
                if body:
                    try:
                        data = json.loads(body.decode())
                    except Exception:
                        data = {}
                epochs = int(data.get("epochs", 40))
                n_images = int(data.get("n_images", 100))
                result = lloyd.image_gen.train_pattern_images(
                    epochs=epochs, n_images=n_images
                )
                if "error" in result:
                    self._json_response(result, status=500)
                    return
                try:
                    lloyd.image_gen.save(BRAIN_DIR / "latest_image_net.npz")
                except Exception:
                    pass
                self._json_response(
                    {
                        "message": result.get(
                            "message",
                            f"trained {epochs} epochs on {n_images} hardcoded pixel arrays",
                        ),
                        **{k: v for k, v in result.items() if k != "message"},
                    }
                )
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)

        elif self.path == "/import":
            try:
                with tempfile.NamedTemporaryFile(suffix=".lloyd", delete=False) as tmp:
                    tmp.write(body)
                    tmp_path = tmp.name
                msg = lloyd.import_brain(tmp_path, trainer=trainer)
                os.unlink(tmp_path)
                self._json_response({"message": msg})
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)

        else:
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
    print(f"Lloyd is live on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
