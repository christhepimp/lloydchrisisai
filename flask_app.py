"""
Lloyd Flask App
===============
Works on PythonAnywhere (and any WSGI host).
Same brain as server.py and the future APK.
Export / import so you can move him later.
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from pathlib import Path
import sys
import os
import tempfile

sys.path.insert(0, str(Path(__file__).parent))

from lloyd.agent import Lloyd
from lloyd.trainer import LloydTrainer

app = Flask(__name__)
lloyd = Lloyd()
trainer = LloydTrainer()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
BRAIN_DIR = Path("brains")
BRAIN_DIR.mkdir(exist_ok=True)
UI_DIR = Path(__file__).parent / "interface" / "mobile_web"

# restore previous brain on startup
_latest = BRAIN_DIR / "latest_brain.npz"
if _latest.exists():
    try:
        trainer.load_brain(_latest)
    except Exception:
        pass
_mem = BRAIN_DIR / "latest_memory.json"
if _mem.exists():
    try:
        lloyd.memory.load(str(_mem))
    except Exception:
        pass


@app.route("/")
def index():
    return send_from_directory(UI_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(UI_DIR, path)


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        user_msg = (data.get("message") or "").strip()
        if not user_msg:
            return jsonify({"reply": "yo say something"})
        reply = lloyd.think(user_msg)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"error: {e}"}), 500


@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"error": "no file"}), 400
        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "empty filename"}), 400

        fname = f"train_{len(list(UPLOAD_DIR.glob('*')))}.txt"
        fpath = UPLOAD_DIR / fname
        content = f.read().decode("utf-8", errors="ignore")
        fpath.write_text(content, encoding="utf-8")

        lloyd.remember(f"User uploaded training file: {fname}")
        return jsonify({
            "status": "ok",
            "filename": fname,
            "message": f"got it. saved as {fname}. hit Train when ready."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/train", methods=["POST"])
def train():
    try:
        files = list(UPLOAD_DIR.glob("*.txt"))
        if not files:
            return jsonify({"message": "no files uploaded yet. upload a .txt first."})

        result = trainer.train_on_files(files, steps_per_file=25)

        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")[:300]
            lloyd.remember(f"Trained on {f.name}: {text}")

        trainer.save_brain(BRAIN_DIR / "latest_brain.npz")
        lloyd.memory.save(str(BRAIN_DIR / "latest_memory.json"))

        return jsonify({
            "message": result["message"] + " " + " | ".join(result.get("reports", [])[:3])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/export", methods=["GET"])
def export_brain():
    try:
        out = BRAIN_DIR / "lloyd_export.lloyd"
        lloyd.export_brain(out, trainer=trainer)
        return send_file(out, as_attachment=True, download_name="lloyd_brain.lloyd")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/import", methods=["POST"])
def import_brain():
    try:
        if "file" in request.files:
            f = request.files["file"]
            with tempfile.NamedTemporaryFile(suffix=".lloyd", delete=False) as tmp:
                f.save(tmp.name)
                msg = lloyd.import_brain(tmp.name, trainer=trainer)
                os.unlink(tmp.name)
        else:
            with tempfile.NamedTemporaryFile(suffix=".lloyd", delete=False) as tmp:
                tmp.write(request.get_data())
                msg = lloyd.import_brain(tmp.name, trainer=trainer)
                os.unlink(tmp.name)
        return jsonify({"message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
