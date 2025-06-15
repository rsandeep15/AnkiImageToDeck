from pathlib import Path
from openai import OpenAI
import sys

from AnkiSync import invoke

def createAudioFile(client, text, fileName):
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="onyx",
        input=text,
        instructions="Speak like a Korean native speaker",
    ) as response:
        response.stream_to_file(Path(__file__).parent / fileName)


def main():
    deckname = sys.argv[1]
    cards = invoke("findNotes", query="deck:{deck_name}".format(deck_name=deckname))
    client = OpenAI()

    for cardID in cards:
        try:
            result = invoke("notesInfo", notes=[cardID])[0]
            frontText = result['fields']['Front']['value']
            backText = result['fields']['Back']['value']
            # print(frontText)
            filename = str(cardID)+".mp3"
            createAudioFile(client, frontText, filename)
            path_to_file = Path(__file__).parent.as_posix() + "/" + filename
            result = invoke("updateNoteFields", note={"id":cardID, "fields": {"Front":frontText, "Back":backText}, "audio": [{"filename":filename, "fields": ["Front"],"path":path_to_file}]})
            noteResult = invoke("notesInfo", notes=[cardID])
            # print(noteResult)
        except Exception as e:
            print(e)
            continue

    cards = invoke("findNotes", query="deck:{deck_name}".format(deck_name=deckname))
    print(cards)


if __name__=="__main__":
    main()