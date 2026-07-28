"""
Lloyd Local Server
==================
Simple pure-Python HTTP server so the mobile UI can talk to the real agent
and support file upload + training.

Run: python server.py
Then open http://localhost:8080
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import urllib.parse
from pathlib import Path

# Make sure we can import lloyd
import sys
sys.path.insert(0, str(Path(__file__).parent))

from lloyd.agent import Lloyd

lloyd = Lloyd()

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
            # Very simple multipart parser for text files
            try:
                content_type = self.headers.get("Content-Type", "")
                if "multipart/form-data" not in content_type:
                    self._json_response({"error": "expected multipart"}, status=400)
                    return

                # Extremely basic extraction (good enough for text files)
                body_str = body.decode("utf-8", errors="ignore")
                # Look for filename and content
                if "filename=" in body_str:
                    # Save raw for now
                    fname = f"train_{len(list(UPLOAD_DIR.glob('*')))}.txt"
                    fpath = UPLOAD_DIR / fname
                    # Extract text after the headers
                    parts = body_str.split("\r\n\r\n", 1)
                    if len(parts) > 1:
                        text = parts[1].split("\r\n--")[0]
                        fpath.write_text(text, encoding="utf-8")
                        # Tell Lloyd about it
                        lloyd.remember(f"User uploaded training file: {fname}")
                        self._json_response({
                            "status": "ok",
                            "filename": fname,
                            "message": f"got it. saved as {fname}. ready to train when you hit train."
                        })
                        return
                self._json_response({"error": "could not parse file"}, status=400)
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)

        elif self.path == "/train":
            try:
                # Simple training trigger using whatever is in uploads
                files = list(UPLOAD_DIR.glob("*.txt"))
                if not files:
                    self._json_response({"message": "no files uploaded yet. upload a .txt first."})
                    return

                # For now just read and remember the content (real token training next)
                total_chars = 0
                for f in files:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    lloyd.remember(f"Training data from {f.name}: {text[:500]}")
                    total_chars += len(text)

                self._json_response({
                    "message": f"trained on {len(files)} file(s), {total_chars} chars. lloyd is learning."
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


def run(port=8080):
    server = HTTPServer(("0.0.0.0", port), LloydHandler)
    print(f"Lloyd server running at http://localhost:{port}")
    print("Open that URL on your phone or computer.")
    print("Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    run()
