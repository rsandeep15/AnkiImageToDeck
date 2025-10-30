import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from AnkiSync import invoke

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def run_script(script_path: Path, args: List[str]):
    env = os.environ.copy()
    if "OPENAI_API_KEY" not in env:
        raise RuntimeError("OPENAI_API_KEY is not set on the server.")

    command = [sys.executable, str(script_path)] + args
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/decks", methods=["GET"])
def list_decks():
    try:
        decks = invoke("deckNames")
        return jsonify({"ok": True, "decks": decks})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


def estimate_sync_duration(card_count: int) -> Tuple[int, str]:
    if card_count <= 0:
        return 30, "About 30 seconds"
    seconds = min(180, max(30, card_count * 4))
    minutes = seconds // 60
    if minutes:
        return seconds, f"Roughly {minutes} minute{'s' if minutes > 1 else ''}"
    return seconds, f"About {seconds} seconds"


def estimate_media_duration(card_count: int, per_card_seconds: float) -> Tuple[int, str]:
    if card_count <= 0:
        return 60, "About 1 minute"
    seconds = int(min(1800, max(45, card_count * per_card_seconds)))
    minutes = seconds // 60
    if minutes:
        return seconds, f"Roughly {minutes} minute{'s' if minutes > 1 else ''}"
    return seconds, f"About {seconds} seconds"


def get_deck_card_count(deckname: str) -> int:
    try:
        cards = invoke("findNotes", query=f"deck:{deckname}")
        return len(cards)
    except Exception:
        return 0


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

    command_args = [str(saved_path)]
    if deck_name:
        command_args.extend(["--deck", deck_name])
    if model:
        command_args.extend(["--model", model])
    if include_romanized:
        command_args.append("--romanized")
    else:
        command_args.append("--no-romanized")

    try:
        result = run_script(BASE_DIR / "AnkiSync.py", command_args)
        deck_for_estimate = deck_name or safe_name.rsplit(".", 1)[0]
        count = get_deck_card_count(deck_for_estimate)
        eta_seconds, eta_text = estimate_sync_duration(count)
        return jsonify(
            {
                "ok": True,
                "message": "Deck synced successfully.",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "eta_seconds": eta_seconds,
                "eta_text": eta_text,
                "items_processed": count,
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
    except RuntimeError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.route("/generate/audio", methods=["POST"])
def generate_audio():
    data = request.get_json(silent=True) or {}
    deck = data.get("deck", "").strip()
    if not deck:
        return jsonify({"ok": False, "message": "Deck name is required."}), 400

    args = [deck]
    model = data.get("model")
    voice = data.get("voice")
    workers = data.get("workers")
    instructions = data.get("instructions")

    if model:
        args.extend(["--model", model])
    if voice:
        args.extend(["--voice", voice])
    if instructions:
        args.extend(["--instructions", instructions])
    if workers:
        args.extend(["--workers", str(workers)])

    try:
        result = run_script(BASE_DIR / "AnkiDeckToSpeech.py", args)
        card_count = get_deck_card_count(deck)
        eta_seconds, eta_text = estimate_media_duration(card_count, per_card_seconds=6.0)
        return jsonify(
            {
                "ok": True,
                "message": "Audio generation completed.",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "eta_seconds": eta_seconds,
                "eta_text": eta_text,
                "items_processed": card_count,
            }
        )
    except subprocess.CalledProcessError as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "Audio generation failed.",
                    "stdout": exc.stdout,
                    "stderr": exc.stderr,
                }
            ),
            500,
        )
    except RuntimeError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.route("/generate/images", methods=["POST"])
def generate_images():
    data = request.get_json(silent=True) or {}
    deck = data.get("deck", "").strip()
    if not deck:
        return jsonify({"ok": False, "message": "Deck name is required."}), 400

    args = [deck]
    image_model = data.get("image_model")
    gating_model = data.get("gating_model")
    prompt = data.get("prompt")
    workers = data.get("workers")
    skip_gating = data.get("skip_gating", False)

    if image_model:
        args.extend(["--image-model", image_model])
    if gating_model:
        args.extend(["--gating-model", gating_model])
    if prompt:
        args.extend(["--prompt", prompt])
    if workers:
        args.extend(["--workers", str(workers)])
    if skip_gating:
        args.append("--skip-gating")

    try:
        result = run_script(BASE_DIR / "AnkiDeckToImages.py", args)
        card_count = get_deck_card_count(deck)
        eta_seconds, eta_text = estimate_media_duration(card_count, per_card_seconds=12.0)
        return jsonify(
            {
                "ok": True,
                "message": "Image generation completed.",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "eta_seconds": eta_seconds,
                "eta_text": eta_text,
                "items_processed": card_count,
            }
        )
    except subprocess.CalledProcessError as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "Image generation failed.",
                    "stdout": exc.stdout,
                    "stderr": exc.stderr,
                }
            ),
            500,
        )
    except RuntimeError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True)
