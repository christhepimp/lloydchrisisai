"""
Lloyd Local + Deployable Server
===============================
Works on localhost and on cloud hosts (Render, Railway, etc.)
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent))

from lloyd.agent import Lloyd
from lloyd.trainer import LloydTrainer

lloyd = Lloyd()
trainer = LloydTrainer()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class LloydHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / "interface" / "mobile_web"), **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
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
                reply = lloyd.think(user_msg)
                self._json_response({"reply": reply})
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
                        self._json_response({
                            "status": "ok",
                            "filename": fname,
                            "message": f"got it. saved as {fname}. hit Train when ready."
                        })
                        return
                self._json_response({"error": "could not parse file"}, status=400)
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)

        elif self.path == "/train":
            try:
                files = list(UPLOAD_DIR.glob("*.txt"))
                if not files:
                    self._json_response({"message": "no files uploaded yet. upload a .txt first."})
                    return

                result = trainer.train_on_files(files, steps_per_file=25)

                for f in files:
                    text = f.read_text(encoding="utf-8", errors="ignore")[:300]
                    lloyd.remember(f"Trained on {f.name}: {text}")

                self._json_response({
                    "message": result["message"] + " " + " | ".join(result.get("reports", [])[:3])
                })
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
    server = HTTPServer(("0.0.0.0", port), LloydHandler)
    print(f"Lloyd is live on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
