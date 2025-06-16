from openai import OpenAI
import base64
import sys
from pathlib import Path
from AnkiSync import invoke

def generate_image(client, text, filename):

    # prompt = "Generate an visual to help remember the given vocabulary word in a flashcard app like Anki: {text}".format(text=text)
    # print(prompt)
    result = client.images.generate(
        model="gpt-image-1",
        prompt="Generate an visual to help remember the given vocabulary word in a flashcard app like Anki: {text}. Do not include the vocab word or any text in the image. Do like anime or cartoon style and not photo realistic.".format(text=text),
    )

    print("Generated image for: " + text)

    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    # Save the image to a file
    with open(filename, "wb") as f:
        f.write(image_bytes)
    return filename

def main():
    deckname = sys.argv[1]
    cards = invoke("findNotes", query="deck:{deck_name}".format(deck_name=deckname))
    client = OpenAI() 
    for cardID in cards:
        try:
            result = invoke("notesInfo", notes=[cardID])[0]
            # Front Text is foreign language, back text is English.
            frontText = result['fields']['Front']['value']
            backText = result['fields']['Back']['value']
            ## Just run it on single words and cards without images yet.
            if "<img" not in frontText and len(frontText.split()) == 1:
                filename = generate_image(client=client, text=backText, filename=str(cardID)+".png")
                path_to_file = Path(__file__).parent.as_posix() + "/" + filename
                result = invoke("updateNoteFields", note={"id":cardID, "fields": {"Front":frontText, "Back":backText}, "picture": [{"filename":filename, "fields": ["Front"],"path":path_to_file}]})
        except Exception as e:
            print(e)
            continue

if __name__=="__main__":
    main()