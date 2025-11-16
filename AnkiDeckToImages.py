import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import re
from typing import Any, List, Tuple

from openai import OpenAI

from AnkiSync import invoke

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
IMAGE_DIR = MEDIA_DIR / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_MAX_WORKERS = 3
HTML_TAG_RE = re.compile(r"<[^>]+>")
IMG_TAG_RE = re.compile(r"<img[^>]*?>", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate illustrative images for Anki notes in a specified deck."
    )
    parser.add_argument("deck", help="Name of the Anki deck to process.")
    parser.add_argument(
        "--image-model",
        default="gpt-image-1",
        help="Image generation model to use (default: %(default)s).",
    )
    parser.add_argument(
        "--gating-model",
        default="gpt-4.1",
        help="Model used to decide whether an image is helpful (default: %(default)s).",
    )
    parser.add_argument(
        "--prompt",
        default=(
            "Generate a memory aid illustration for this Anki flashcard concept: {text}. "
            "Do not include any words or letters. Favor stylized anime/cartoon aesthetics, not photorealism."
        ),
        help="Template used for image generation; {text} is replaced with the back of the card.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("ANKI_IMAGE_WORKERS", str(DEFAULT_MAX_WORKERS))),
        help="Maximum number of concurrent generations (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-gating",
        action="store_true",
        help="Generate images for every eligible card without the gating check.",
    )
    return parser.parse_args()


def load_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Environment variable OPENAI_API_KEY is not set.")
    return api_key


def get_candidate_cards(deckname: str) -> List[Tuple[int, str, str]]:
    cards = invoke("findNotes", query=f"deck:{deckname}")
    if not cards:
        return []
    notes_info = invoke("notesInfo", notes=cards)
    candidates: List[Tuple[int, str, str]] = []
    for card_id, note in zip(cards, notes_info):
        front_text = note["fields"]["Front"]["value"]
        back_text = note["fields"]["Back"]["value"]
        candidates.append((card_id, front_text, back_text))
    return candidates


def sanitize_text(text: str) -> str:
    """Strip HTML tags and collapse whitespace for cleaner prompts."""
    without_tags = HTML_TAG_RE.sub(" ", text)
    return " ".join(without_tags.split())


def strip_image_tags(text: str) -> str:
    """Remove any <img> tags so we can replace or delete them cleanly."""
    return IMG_TAG_RE.sub("", text)


def build_image_prompt(template: str, concept: str) -> str:
    return template.format(text=concept)


def generate_image(
    client: OpenAI,
    prompt: str,
    filename: str,
    *,
    model: str,
) -> Path:
    result = client.images.generate(
        model=model,
        prompt=prompt,
    )
    image_base64 = result.data[0].b64_json
    target_path = IMAGE_DIR / filename
    with open(target_path, "wb") as handle:
        handle.write(base64.b64decode(image_base64))
    return target_path.resolve()


def get_response_text(resp: Any) -> str:
    text = getattr(resp, "output_text", None)
    if text:
        return text
    output = getattr(resp, "output", None)
    if not output:
        return ""
    parts: List[str] = []
    for item in output:
        for content_piece in getattr(item, "content", []):
            maybe_text = getattr(content_piece, "text", None)
            if maybe_text:
                parts.append(maybe_text)
    return "".join(parts)


def should_generate_image(
    client: OpenAI,
    front_text: str,
    back_text: str,
    *,
    model: str,
) -> bool:
    gating_prompt = (
        "Given this flashcard pair, decide if a visual aid would help memorization.\n"
        f"Front: {front_text}\n"
        f"Back: {back_text}\n"
        "Reply strictly with true or false in lowercase. Use true for concrete nouns or phrases "
        "where imagery aids recall. Use false if an image would be redundant or misleading."
    )
    response = client.responses.create(
        model=model,
        input=gating_prompt,
    )
    decision = get_response_text(response).strip().lower()
    return decision == "true"


def process_card(
    card: Tuple[int, str, str],
    api_key: str,
    image_model: str,
    gating_model: str,
    prompt_template: str,
    skip_gating: bool,
) -> Tuple[str, str, Any]:
    card_id, front_text, back_text = card
    local_client = OpenAI(api_key=api_key)
    front_without_images = strip_image_tags(front_text)
    back_without_images = strip_image_tags(back_text)
    cleaned_back = sanitize_text(back_without_images)
    if not cleaned_back:
        return ("skip", back_without_images, "No descriptive text after cleaning.")

    try:
        if not skip_gating:
            cleaned_front = sanitize_text(front_without_images)
            if not should_generate_image(
                local_client,
                cleaned_front or front_without_images,
                cleaned_back,
                model=gating_model,
            ):
                if (
                    front_without_images != front_text
                    or back_without_images != back_text
                ):
                    invoke(
                        "updateNoteFields",
                        note={
                            "id": card_id,
                            "fields": {
                                "Front": front_without_images,
                                "Back": back_without_images,
                            },
                        },
                    )
                    return (
                        "skip",
                        back_without_images,
                        "Gating model returned false; existing image removed.",
                    )
                return ("skip", back_without_images, "Gating model returned false.")

        filename = f"{card_id}.png"
        prompt = build_image_prompt(prompt_template, cleaned_back)
        file_path = generate_image(local_client, prompt, filename, model=image_model)
        invoke(
            "updateNoteFields",
            note={
                "id": card_id,
                "fields": {
                    "Front": front_without_images,
                    "Back": back_without_images,
                },
                "picture": [
                    {
                        "filename": filename,
                        "fields": ["Front"],
                        "path": file_path.as_posix(),
                    }
                ],
            },
        )
        return ("added", back_text, None)
    except Exception as exc:
        return ("error", back_text, exc)


def main() -> None:
    args = parse_args()
    api_key = load_api_key()

    print(f"Fetching notes for deck: {args.deck}")
    candidates = get_candidate_cards(args.deck)
    if not candidates:
        print(f"No cards eligible for image generation in deck '{args.deck}'.")
        return

    worker_limit = max(1, args.workers)
    max_workers = max(1, min(worker_limit, len(candidates)))
    prompt_template = args.prompt.strip()
    print(
        f"Generating images with up to {max_workers} worker(s) using image model {args.image_model} "
        f"and gating model {args.gating_model if not args.skip_gating else 'skipped'}."
    )

    added = skipped = failed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_card,
                card,
                api_key,
                args.image_model,
                args.gating_model,
                prompt_template,
                args.skip_gating,
            )
            for card in candidates
        ]
        for future in as_completed(futures):
            status, back_text, error = future.result()
            if status == "added":
                print(f"Adding image for: {back_text}")
                added += 1
            elif status == "skip":
                print(f"Skipping image for: {back_text} ({error})")
                skipped += 1
            else:
                print(f"Failed image for: {back_text} ({error})")
                failed += 1

    print(f"Completed image generation: {added} added, {skipped} skipped, {failed} failed.")


if __name__ == "__main__":
    main()
