import config
import os
import openai
import json
import numpy as np
from numpy.linalg import norm
import re
from time import time,sleep
from uuid import uuid4
import datetime
import pinecone

debug = True
# Initialize OpenAI API
openai.api_key = config.OPENAI_API_KEY

# Initialize Pinecone API
pinecone_api_key = config.PINECONE_API
pinecone_region = config.PINECONE_REGION
pinecone_index = config.PINECONE_INDEX
prompt_keywords_instructions = config.PROMPT_KEYWORDS_INSTRUCTIONS
prompt_chat = config.PROMPT_CHAT
last_keywords = []

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


def save_file(filepath, content):
    # Create the directory if it does not exist
    directory = os.path.dirname(filepath)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return json.load(infile)


def save_json(filepath, payload):
    # Create the directory if it does not exist
    directory = os.path.dirname(filepath)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(filepath, 'w', encoding='utf-8') as outfile:
        json.dump(payload, outfile, ensure_ascii=False, sort_keys=True, indent=2)


def timestamp_to_datetime(unix_time):
    return datetime.datetime.fromtimestamp(unix_time).strftime("%A, %B %d, %Y at %I:%M%p %Z")


def gpt3_embedding(content, engine='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()  # fix any UNICODE errors
    response = openai.Embedding.create(input=content,engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector

def chatgpt_completion(messages, prompt):
    model="gpt-3.5-turbo"
    global last_keywords
    response = openai.ChatCompletion.create(model=model, messages=messages)
    text = response['choices'][0]['message']['content']
    filename = 'chat_%s_gpt3.txt' % time()
    if not os.path.exists('chat_logs'):
        os.makedirs('chat_logs')
    keywords = generate_keyword_list(prompt)
    last_keywords = keywords
    save_file('chat_logs/%s' % filename, prompt + '\n\n==========\n\n' + text)
    # save keywords to a file
    if (last_keywords is not None):
        keyfilename = 'keywords_%d.json' % int(time())
        save_file('keywords_logs/%s' % keyfilename, last_keywords)
    return text

def load_last_recent_keywords():
    keywords_dir = 'keywords_logs'
    if not os.path.exists(keywords_dir):
        return []

    files = [os.path.join(keywords_dir, f) for f in os.listdir(keywords_dir) if os.path.isfile(os.path.join(keywords_dir, f))]
    if not files:
        return []

    latest_file = max(files, key=os.path.getctime)
    return json.loads(open_file(latest_file))

last_keywords = load_last_recent_keywords()

def generate_keyword_list(text):
    if debug: print("generating keywords for: ", text)
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": prompt_keywords_instructions},{"role": "user", "content": "this is not a conversation, this is the text you need to convert to keywords: '" + text + "'"}], temperature=0)
    newtext = response['choices'][0]['message']['content']
    if debug: print("keywords generated: ", newtext)
    # check if text contains a json string
    json_string = extract_json_string(newtext)
    if json_string:
        try:
            keywords = json.loads(json_string)
            return json.dumps(keywords)
        except:
            if debug: print("Error: keywords not in json format")
            if debug: print(json_string)
            return None
    else:
        if debug: print("Error: no JSON found in the text")
        return None

def extract_json_string(text):
    # Find the starting and ending indices of the JSON string
    start_index = text.find('{')
    end_index = text.rfind('}')

    if start_index != -1 and end_index != -1:
        json_string = text[start_index:end_index + 1]

        # Replace escaped double quotes with regular double quotes
        json_string = json_string.replace('\\"', '"')

        try:
            json.loads(json_string)
            return json_string
        except json.JSONDecodeError:
            pass

    # Fallback to the regular expression method
    json_string = re.search(r'\{(?:[^{}]|"(?:\\.|[^"\\])*")*\}', text)

    if json_string:
        json_string = json_string.group()

        # Replace escaped double quotes with regular double quotes
        json_string = json_string.replace('\\"', '"')

        try:
            json.loads(json_string)
            return json_string
        except json.JSONDecodeError:
            pass

    return None

def load_conversation(results):
    result = list()
    for m in results['matches']:
        try:
            info = load_json('messages/%s.json' % m['id'])
            result.append(info)
        except FileNotFoundError:
            if debug: print("File not found: 'messages/%s.json'" % m['id'])
    ordered = sorted(result, key=lambda d: d['time'], reverse=False)  # sort them all chronologically
    output = ""
    for i in ordered:
        line = i['speaker'] + ': ' + i['message']
        output += line + '\n'
    return output


if __name__ == '__main__':
    convo_length = 30
    pinecone.init(api_key=pinecone_api_key, environment=pinecone_region)
    vdb = pinecone.Index(pinecone_index)
    vdb
    while True:
        #### get user input, save it, vectorize it, save to pinecone
        payload = list()
        a = input('\n\nUSER: ')
        timestamp = time()
        timestring = timestamp_to_datetime(timestamp)
        #message = '%s: %s - %s' % ('USER', timestring, a)
        message = a
        vector = gpt3_embedding(message)
        unique_id = str(uuid4())
        metadata = {'speaker': 'USER', 'time': timestamp, 'message': message, 'timestring': timestring, 'uuid': unique_id}
        save_json('messages/%s.json' % unique_id, metadata)
        payload.append((unique_id, vector))
        #### search for relevant messages, and generate a response
        results = vdb.query(vector=vector, top_k=convo_length, namespace='AIROBIN')
        conversation = load_conversation(results)  # results should be a DICT with 'matches' which is a LIST of DICTS, with 'id'
        #### load keywords
        keywords = "keywords: " + json.dumps(last_keywords)
        #### generate prompt
        prompt = open_file('prompt_response.txt').replace('<<CONVERSATION>>', conversation).replace('<<MESSAGE>>', a).replace('<<MEMORY>>', keywords)
        #### generate response, vectorize, save, etc
        #output = gpt3_completion(prompt) # gpt3 and lower
        # gpt3.5 and higher
        messages = [ 
            {
                "role": "system",
                "content": prompt_chat
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        output = chatgpt_completion(messages, prompt)
        timestamp = time()
        timestring = timestamp_to_datetime(timestamp)
        message = output
        vector = gpt3_embedding(message)
        unique_id = str(uuid4())
        metadata = {'speaker': 'AIROBIN', 'time': timestamp, 'message': message, 'timestring': timestring, 'uuid': unique_id}
        save_json('messages/%s.json' % unique_id, metadata)
        payload.append((unique_id, vector))
        vdb.upsert(payload, namespace='AIROBIN')
        print('\nAIROBIN: %s' % output) 