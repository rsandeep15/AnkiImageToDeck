import os
from openai import OpenAI
import sys
import json
import urllib.request

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


# Function to create a file with the Files API
def create_file(file_path):
  with open(file_path, "rb") as file_content:
    result = client.files.create(
        file=file_content,
        purpose="assistants",
    )
    return result.id

# Getting the file ID
filename = sys.argv[1]
file_id = create_file(filename)

response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", 
             "text": "Read this pdp and return a list of English Word; Foreign Word. Include the romanized characters next to the foreign word in parenthesis if available."
            "Do not prefix your response with anything and just provide the list, with semicolon delimiter splitting each word."},
            {
                "type": "input_file",
                "file_id": file_id,
            },
        ],
    }],
)

word_pairs = response.output_text.splitlines()

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

deckname = sys.argv[2]
invoke('createDeck', deck=deckname)

notes = {}
for vocab_pair in word_pairs:
    try:
        # print(vocab_pair)
        english, foreign_word = vocab_pair.split(';')
        note = {
            "deckName": deckname,
            "modelName": "Basic",
            "fields": {
                "Front": foreign_word,
                "Back": english
            }
         }
        notes[foreign_word] = note
    except:
        continue
    


result = invoke("addNotes", notes=list(notes.values()))


