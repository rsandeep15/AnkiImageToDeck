import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/sync", methods=["POST"])
def sync_deck():
    uploaded_file = request.files.get("file")
    deck_name = request.form.get("deck", "").strip()
    model = request.form.get("model", "").strip() or "gpt-4.1-mini"
    include_romanized = request.form.get("romanized", "true") == "true"

    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"ok": False, "message": "No PDF uploaded."}), 400

    if not allowed_file(uploaded_file.filename):
        return jsonify({"ok": False, "message": "Only PDF files are supported."}), 400

    safe_name = secure_filename(uploaded_file.filename)
    saved_path = UPLOAD_DIR / safe_name
    uploaded_file.save(saved_path)

    env = os.environ.copy()
    if "OPENAI_API_KEY" not in env:
        return jsonify({"ok": False, "message": "OPENAI_API_KEY is not set on the server."}), 500

    command = [sys.executable, "AnkiSync.py", str(saved_path)]
    if deck_name:
        command.extend(["--deck", deck_name])
    if model:
        command.extend(["--model", model])
    if include_romanized:
        command.append("--romanized")
    else:
        command.append("--no-romanized")

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return jsonify(
            {
                "ok": True,
                "message": "Deck synced successfully.",
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    except subprocess.CalledProcessError as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "AnkiSync failed.",
                    "stdout": exc.stdout,
                    "stderr": exc.stderr,
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(debug=True)
