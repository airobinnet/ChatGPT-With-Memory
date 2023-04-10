from flask import Flask, make_response, request, jsonify
from flask_cors import CORS
import requests
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
import random
from operator import itemgetter
import glob


debug = True
# Initialize OpenAI API
openai.api_key = config.OPENAI_API_KEY

# Initialize Pinecone API
pinecone_api_key = config.PINECONE_API
pinecone_region = config.PINECONE_REGION
pinecone_index = config.PINECONE_INDEX
prompt_keywords_instructions = config.PROMPT_KEYWORDS_INSTRUCTIONS
prompt_chat = config.PROMPT_CHAT
chosen_model = config.CHATGPT_MODEL
keyword_model = config.CHATGPT_MODEL_KEYWORDS
pinecone_namespace = config.PINECONE_NAMESPACE
max_reply_tokens = config.MAX_REPLY_TOKENS

# ANSI color codes for printing to console
red = '\033[91m'     # soft red
green = '\033[92m'   # soft green
yellow = '\033[93m'  # soft yellow
blue = '\033[94m'    # soft blue
magenta = '\033[95m' # soft magenta
cyan = '\033[96m'    # soft cyan
white = '\033[97m'   # soft white
reset = '\033[0m'    # reset color

last_keywords = []

# take another function as an argument and handles the retries with exponential backoff.
# preventing the script from crashing due to temporary connection issues
def exponential_backoff(func, *args, **kwargs):
    max_retries = kwargs.pop('max_retries', 5)
    base_delay = kwargs.pop('base_delay', 1)
    max_delay = kwargs.pop('max_delay', 60)

    retries = 0
    while retries <= max_retries:
        try:
            return func(*args, **kwargs)
        except (openai.error.APIConnectionError, requests.exceptions.RequestException) as e:
            if retries == max_retries:
                raise e

            delay = min(max_delay, base_delay * (2 ** retries)) + random.uniform(0, 0.1 * (2 ** retries))
            retries += 1
            sleep(delay)

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

def save_json(file_path, data):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory) and directory:
        os.makedirs(directory)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

def update_index(index_file, username, message_metadata):
    if os.path.exists(index_file):
        index_data = load_json(index_file)
    else:
        index_data = {}

    if username not in index_data:
        index_data[username] = []

    index_data[username].append(message_metadata)

    save_json(index_file, index_data)

def timestamp_to_datetime(unix_time):
    return datetime.datetime.fromtimestamp(unix_time).strftime("%A, %B %d, %Y at %I:%M%p %Z")


def gpt3_embedding(content, engine='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()  # fix any UNICODE errors
    response = exponential_backoff(openai.Embedding.create, input=content, engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector

def chatgpt_completion(messages, prompt):
    model=chosen_model
    global last_keywords
    response = exponential_backoff(openai.ChatCompletion.create, model=model, messages=messages, max_tokens = max_reply_tokens)
    text = response['choices'][0]['message']['content']
    filename = 'chat_%s_gpt3.txt' % time()
    if not os.path.exists('chat_logs'):
        os.makedirs('chat_logs')
    keywords = generate_keyword_list(prompt)
    last_keywords = keywords
    save_file('chat_logs/%s' % filename, prompt  + '\n' + text + '\n\n==========\n\n')
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
    if debug: print(red + "generating keywords for: ", text  + reset)
    response = exponential_backoff(openai.ChatCompletion.create ,model=keyword_model, messages=[{"role": "system", "content": prompt_keywords_instructions},{"role": "user", "content": "this is not a conversation, this is the text you need to convert to long term memory-keywords: '" + text + "'"}], temperature=0)
    newtext = response['choices'][0]['message']['content']
    if debug: print(yellow + "keywords generated: ", newtext + reset)
    # check if text contains a json string
    json_string = extract_json_string(newtext)
    if json_string:
        try:
            keywords = json.loads(json_string)
            return json.dumps(keywords)
        except:
            if debug: print(blue + "Error: keywords not in json format" + reset)
            if debug: print(blue + json_string + reset)
            return None
    else:
        if debug: print(blue + "Error: no JSON found in the text" + reset)
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

def recent_conversations(username, amount):
    message_files = glob.glob("messages/*.json")
    message_files.sort(key=os.path.getmtime, reverse=True)

    recent_messages = []
    for message_file in message_files:
        message_data = load_json(message_file)
        if message_data["speaker"] == username:
            recent_messages.append(message_data)
            if len(recent_messages) == amount+1:
                break

    recent_messages.pop(0)

    output = ""
    for message in reversed(recent_messages):
        msg_time = message['time']
        message_time = datetime.datetime.fromtimestamp(float(msg_time))
        output += f"({message_time.strftime('%Y-%m-%d %H:%M:%S')}) {message['speaker']}: {message['message']}\n"

        # Find the corresponding reply
        reply_msgid = message['msgid']
        for reply_file in message_files:
            reply_data = load_json(reply_file)
            if reply_data["speaker"] == "AIROBIN" and reply_data.get("target") == username and reply_data["msgid"] == reply_msgid:
                reply_time = reply_data['time']
                reply_message_time = datetime.datetime.fromtimestamp(float(reply_time))
                output += f"({reply_message_time.strftime('%Y-%m-%d %H:%M:%S')}) {reply_data['speaker']}: {reply_data['message']}\n\n"
                break

    return output

def load_conversation(results):
    result = list()
    for m in results['matches']:
        try:
            info = load_json('messages/%s.json' % m['id'])
            result.append(info)
        except FileNotFoundError:
            if debug: print(magenta + "File not found: 'messages/%s.json'" % m['id'] + reset)
    ordered = sorted(result, key=lambda d: d['time'], reverse=False)  # sort them all chronologically
    output = ""
    for i in ordered:
        msg_time = i['time']
        message_time = datetime.datetime.fromtimestamp(float(msg_time))
        line = "(" + message_time.strftime('%Y-%m-%d %H:%M:%S') + ") " + i['speaker'] + ': ' + i['message']
        output += line + '\n'
    return output

app = Flask(__name__)
CORS(app)

@app.route('/chat', methods=['POST', "OPTIONS"])
def chat():
    if request.method == "OPTIONS":  # CORS preflight
        return _build_cors_preflight_response()
    user_input = request.json.get('user_input')
    username = request.json.get('username')
    if not user_input:
        return jsonify({'error': 'Missing user_input field in request data'}), 400
    if not username:
        return jsonify({'error': 'Missing username field in request data'}), 400
    # setting the convo_length to 20, but this can be changed later if gpt4 offers more tokens
    # if you get too many errors that the prompt is too long, you can reduce this number
    # but this will also reduce the 'memory' of the past conversations
    convo_length = 20
    pinecone.init(api_key=pinecone_api_key, environment=pinecone_region)
    vdb = pinecone.Index(pinecone_index)
    vdb
    while True:
        #### get user input, save it, vectorize it, save to pinecone
        payload = list()
        a = user_input
        timestamp = time()
        timestring = timestamp_to_datetime(timestamp)
        #message = '%s: %s - %s' % ('USER', timestring, a)
        message = a
        vector = gpt3_embedding(message)
        msg_id = str(uuid4())
        unique_id = str(uuid4())
        metadata = {'speaker': username, 'time': timestamp, 'message': message, 'timestring': timestring, 'uuid': unique_id, 'msgid': msg_id}
        save_json('messages/%s.json' % unique_id, metadata)
        payload.append((unique_id, vector))
        #### search for relevant messages, and generate a response
        results = vdb.query(vector=vector, top_k=convo_length, namespace=pinecone_namespace)
        conversation = load_conversation(results)  # results should be a DICT with 'matches' which is a LIST of DICTS, with 'id'
        #### load keywords
        keywords = "keywords: " + json.dumps(last_keywords)
        #### generate prompt
        # set the date to dd/mm/yyyy hh:mm:ss
        current_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        last_3_messages = recent_conversations(username, 3)
        prompt = open_file('prompt_response.txt').replace('<<CONVERSATION>>', conversation).replace('<<MESSAGE>>', username + ": " + a).replace('<<MEMORY>>', keywords).replace('<<DATE>>', current_date).replace('<<RECENT_MESSAGES>>', last_3_messages).replace('<<USERNAME>>', username)
        #### generate response, vectorize, save, etc
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
        metadata = {'speaker': 'AIROBIN', 'target': username, 'time': timestamp, 'message': message, 'timestring': timestring, 'uuid': unique_id, 'msgid': msg_id}
        save_json('messages/%s.json' % unique_id, metadata)
        payload.append((unique_id, vector))
        exponential_backoff(vdb.upsert ,payload, namespace=pinecone_namespace)
        if debug: print(cyan + '\nAIROBIN: %s' % output + reset) 
        if request.method == "POST": # The actual request following the preflight
            return _corsify_actual_response(jsonify({'airobin_response': output}))
        else:
            raise RuntimeError("Weird - don't know how to handle method {}".format(request.method))

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    response.status_code = 200
    return response

def _corsify_actual_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)