import os
from openai import OpenAI
import sys
# import csv
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
        purpose="vision",
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
            {"type": "input_text", "text": "Read this image and represent it in CSV format as English Word, Korean Word. Do not prefix your response with anything and just provide the list."},
            {
                "type": "input_image",
                "file_id": file_id,
            },
        ],
    }],
)

english_korean_pairs = response.output_text.splitlines()


# with open('output.csv', 'w', newline='') as csvfile:
#     writer = csv.writer(csvfile)
#     for pair in english_korean_pairs:
#         english, korean = pair.split(',')  # Split only at the first comma
#         writer.writerow([english.strip(), korean.strip()])

# csv_path = os.path.abspath(csvfile.name)
# print(csv_path)

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



notes = []
for vocab_pair in english_korean_pairs:
    english, korean = vocab_pair.split(',')
    note = {
        "deckName": deckname,
        "modelName": "Basic",
        "fields": {
            "Front": korean,
            "Back": english
        }
    }
    notes.append(note)


result = invoke("addNotes", notes=notes)
print(result)


