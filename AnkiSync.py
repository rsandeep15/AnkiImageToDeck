import os
from openai import OpenAI
import sys
import json
import urllib.request

# Function to create a file with the Files API
def create_file(client, file_path):
  with open(file_path, "rb") as file_content:
    result = client.files.create(
        file=file_content,
        purpose="assistants",
    )
    return result.id

def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']


def main(): 
    """
    Given a PDF file, this script converts it to a list of English word to foreign word pairs.
    The pairs are then added to an Anki deck as flashcards.
    The foreign word is the front of the card and the English word is the back.
    The deck is created with the name of the second argument passed to the script.
    """
    client = OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    # Getting the file ID
    filename = sys.argv[1]
    file_id = create_file(client, filename)

    response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", 
             "text": "Read this pdp and return a list of English Word; Foreign Word and separate each pair with a new line. Include the romanized characters next to the foreign word in parenthesis if available."
            "Do not prefix your response with anything. Each line should look like English Word; Foreign Word"},
            {
                "type": "input_file",
                "file_id": file_id,
            },
        ],
    }],
)

    word_pairs = response.output_text.splitlines()
    deckname = sys.argv[2]
    invoke('createDeck', deck=deckname)

    notes = {}
    for vocab_pair in word_pairs:
        try:
            print(vocab_pair)
            english, foreign_word = vocab_pair.split(';')
            note = {
                "deckName": deckname,
                "modelName": "Basic (type in the answer)",
                "fields": {
                    "Front": foreign_word,
                    "Back": english
                }
            }
            notes[foreign_word] = note
        except:
            continue
        
    invoke("addNotes", notes=list(notes.values()))

if __name__=="__main__":
    main()


