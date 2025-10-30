from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from openai import OpenAI
import base64
import sys
from pathlib import Path
from AnkiSync import invoke

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
IMAGE_DIR = MEDIA_DIR / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
MAX_WORKERS = max(1, int(os.environ.get("ANKI_IMAGE_WORKERS", "3")))


def generate_image(client, text, target_path: Path):

    # prompt = "Generate an visual to help remember the given vocabulary word in a flashcard app like Anki: {text}".format(text=text)
    # print(prompt)
    result = client.images.generate(
        model="gpt-image-1",
        prompt="Generate an visual to help remember the given vocabulary word or phrase in a flashcard app like Anki: {text}. Do not include the vocab word or any text in the image. Do like anime or cartoon style and not photo realistic.".format(text=text),
    )

    # print("Generated image for: " + text)

    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    # Save the image to a file
    with open(target_path, "wb") as f:
        f.write(image_bytes)
    return target_path

def check_phrase(client: OpenAI, frontText: str, backText: str) -> bool:
    response = client.responses.create(
        model="gpt-4.1",
        input="Read this pairing of words {frontText} and {backText} and determine if an image would be helpful to memorize the word in Anki. " \
        "If a word sounds really similar in both languages, reply 'false'. Single word nouns are likely to be useful to have a visual. You must reply 'true' or 'false' without any other explanation in all lowercase".format(frontText=frontText, backText=backText),
    )
    return response.output_text.strip() == "true"


def main():
    deckname = sys.argv[1]
    cards = invoke("findNotes", query="deck:{deck_name}".format(deck_name=deckname))

    if not cards:
        print("No cards found for deck:", deckname)
        return

    notes_info = invoke("notesInfo", notes=cards)

    candidates = []
    for cardID, note in zip(cards, notes_info):
        frontText = note['fields']['Front']['value']
        backText = note['fields']['Back']['value']
        if "<img" in frontText:
            print("Skipping image for (already has image): " + backText)
            continue
        candidates.append((cardID, frontText, backText))

    if not candidates:
        print("No cards eligible for image generation.")
        return

    def process_card(cardID, frontText, backText):
        local_client = OpenAI()
        try:
            if not check_phrase(local_client, frontText, backText):
                return ("skip", backText, None)
            filename = str(cardID) + ".png"
            file_path = generate_image(client=local_client, text=backText, target_path=IMAGE_DIR / filename).resolve()
            invoke("updateNoteFields", note={"id":cardID, "fields": {"Front":frontText, "Back":backText}, "picture": [{"filename":filename, "fields": ["Front"],"path":file_path.as_posix()}]})
            return ("added", backText, None)
        except Exception as exc:
            return ("error", backText, exc)

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(candidates))) as executor:
        futures = [executor.submit(process_card, *candidate) for candidate in candidates]
        for future in as_completed(futures):
            status, backText, error = future.result()
            if status == "added":
                print("Adding image for: " + backText)
            elif status == "skip":
                print("Skipping image for: " + backText)
            else:
                print("Failed image for: {text} ({err})".format(text=backText, err=error))

if __name__=="__main__":
    main()
