import os
from openai import OpenAI
import sys
import csv

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
file_id = create_file(sys.argv[1])

response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Read this image and represent it as a CSV format as English Word, Korean Word. Do not prefix your response with anything and just provide the list."},
            {
                "type": "input_image",
                "file_id": file_id,
            },
        ],
    }],
)

english_korean_pairs = response.output_text.splitlines()
with open('output.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    for pair in english_korean_pairs:
        # print(pair)
        english, korean = pair.split(',')  # Split only at the first comma
        writer.writerow([english.strip(), korean.strip()])