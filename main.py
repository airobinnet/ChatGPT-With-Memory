from flask import Flask, make_response, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
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
from plugins.websearch import websearch, webvisit
from plugins.diagram import draw_diagram
from  processing import (open_file, save_file, load_json, save_json, update_index, timestamp_to_datetime, 
                         load_last_recent_keywords, load_conversation, extract_json_string, recent_conversations
                         )
from ansicolors import red, green, yellow, blue, magenta, cyan, white, reset, pink, purple

debug = config.DEBUG
# Initialize OpenAI API
openai.api_key = config.OPENAI_API_KEY

# Initialize Pinecone API
pinecone_api_key = config.PINECONE_API
pinecone_region = config.PINECONE_REGION
pinecone_index = config.PINECONE_INDEX

# Initialize google search API
google_api_key = config.GOOGLE_CSE_API
google_cx = config.GOOGLE_CSE_ID

prompt_keywords_instructions = config.PROMPT_KEYWORDS_INSTRUCTIONS
prompt_search = config.PROMPT_SEARCH
prompt_chat = config.PROMPT_CHAT
chosen_model = config.CHATGPT_MODEL
keyword_model = config.CHATGPT_MODEL_KEYWORDS
summary_model = config.CHATGPT_MODEL_SUMMARY
pinecone_namespace = config.PINECONE_NAMESPACE
max_reply_tokens = config.MAX_REPLY_TOKENS
prompt_thoughts = config.PROMPT_THOUGHTS

last_keywords = []

retries = 0

diagram_image = None

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


def gpt3_embedding(content, engine='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()  # fix any UNICODE errors
    response = exponential_backoff(openai.Embedding.create, input=content, engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector

def ensure_brackets(input_string):
    if not input_string.strip().startswith('[') or not input_string.strip().endswith(']'):
        return f'[{input_string.strip()}]'
    return input_string

def escape_double_quotes(input_string):
    escaped_double_quotes = re.sub(r'(?<!\\)"', r'\"', input_string)
    return escaped_double_quotes.replace("'", '"')

def parse_input(input_json):
    actions = []
    print(input_json)
    for item in input_json:
        action = item["action"]
        value = item.get("value", None)
        actions.append({"action": action, "value": value})

    return actions

def chatgpt_process_thoughts(socketio, question, searchresult, searchquery, summary, nr):
    global retries
    if nr > 3:
        retries = 0
        return summary
    else:
        nr += 1
        retries = nr
        final_response = ''
        current_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        thought_process = prompt_thoughts.replace('<<QUESTION>>', question).replace('<<SEARCH_QUERY>>', searchquery).replace('<<SEARCH_DATA>>', searchresult).replace('<<SUMMARY>>', summary).replace('<<DATE>>', current_date)
        messages = [ 
                {
                    "role": "user",
                    "content": thought_process
                }
            ]
        if debug: print(pink + "thought process: ", thought_process + reset)
        new_response = exponential_backoff(openai.ChatCompletion.create, model=chosen_model, messages=messages, max_tokens = 2000, temperature=0.1)
        result = new_response['choices'][0]['message']['content']
        if debug: print(pink + "new response: ", result + reset)
        bracketed_input = ensure_brackets(result)
        print(bracketed_input)
        actions = []
        for line in bracketed_input.splitlines():
            actions.extend(parse_input(json.loads(line.strip())))
        actions = parse_input(json.loads(bracketed_input))
        search_output = ""
        visit_output = ""
        continue_output = ""
        summary_output = ""
        error_output = ""

        for action in actions:
            if action['action'] == 'search':
                search_output = f"[SEARCHING FOR {action['value']}]"
            elif action['action'] == 'visit':
                visit_output = f"[VISIT WEBSITE {action['value']}]"
            elif action['action'] == 'continue':
                continue_output = summary_output
            elif action['action'] == 'summary':
                summary_output = action['value']
            else:
                error_output = action['value']
            

        output = ""

        if search_output:
            output = chatgpt_online(socketio, search_output, "", "", question, True, str(summary_output))
        elif visit_output:
            output = chatgpt_online(socketio, visit_output, "", "", question, False, str(summary_output))
        elif continue_output:
            output = continue_output
        elif summary_output:
            output = summary_output
        else:
            output = error_output

        print(output.strip())
        output_msg = [ 
                {
                    "role": "user",
                    "content": "convert this text to a readable markdown format, only responce with the converted text: " + output
                }
            ]
        new_output = exponential_backoff(openai.ChatCompletion.create, model=summary_model, messages=output_msg, temperature=0.2)
        result = new_output['choices'][0]['message']['content']
        
        print(result)
        return result

def chatgpt_online(socketio, query, prompt, messages, message=None, search=False, summary=""):
    global retries
    # if the response is a websearch command, then we need to do process it
    if search:
        if debug: print(green + "found websearch command: ", query + reset)
        # get the search output from the response, text is in format [SEARCHING FOR <search term>]
        # output is top x search results + a excerpt from the x'th result
        searchdata = websearch(query, google_api_key, google_cx)
        # if debug: print(green + "search data: ", searchdata + reset)
        current_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        full_search_prompt = prompt_search.replace('<<SEARCH_DATA>>', searchdata).replace('<<QUESTION>>', message).replace('<<SUMMARY>>', summary).replace('<<DATE>>', current_date).replace('<<SEARCH_QUERY>>', query)
        if debug: print(green + "full search prompt: ", full_search_prompt + reset)
        messages = [ 
            {
                "role": "user",
                "content": full_search_prompt
            }
        ]
        # get a new response from the chatbot based on the search results
        new_response = exponential_backoff(openai.ChatCompletion.create, model=chosen_model, messages=messages, max_tokens = max_reply_tokens, temperature=0.2)
        text = new_response['choices'][0]['message']['content']
        result = chatgpt_process_thoughts(socketio, message, searchdata, query, text, retries)
        return result
    else:
        if debug: print(green + "found webvisit command: ", query + reset)
        webdata = webvisit(query)
        messages = [ 
            {
                "role": "user",
                "content": message + "\n" + webdata
            }
        ]
        new_response = exponential_backoff(openai.ChatCompletion.create, model=chosen_model, messages=messages, max_tokens = max_reply_tokens, temperature=0.2)
        text = new_response['choices'][0]['message']['content']
        result = chatgpt_process_thoughts(socketio, message, "", query, text, retries)
        return result
    
def chatgpt_completion(socketio, messages, prompt, message=None):
    global diagram_image
    # messages = json
    # prompt = prompt_response with replaced strings
    # message = most recent message from user
    model=chosen_model
    global last_keywords
    response = exponential_backoff(openai.ChatCompletion.create, model=model, messages=messages, max_tokens = max_reply_tokens, temperature=0.2)
    # the response is either normal text or a command
    text = response['choices'][0]['message']['content']
    # check if the response is a command
    pattern = r'\[(?:SEARCH|SEARCHING) FOR (.+)\]'
    websearch_match = re.match(pattern, text)
    pattern2 = r'\[(?:VISIT|VISITING) WEBSITE (.+)\]'
    webvisit_match = re.match(pattern2, text)
    # Check if input starts with [DIAGRAM]
    if re.search(r'\[(?:DRAW|DRAWING)? DIAGRAM\]', text):
        # Split the text using the [DRAW DIAGRAM] pattern
        parts = re.split(r'\[(?:DRAW|DRAWING)? DIAGRAM\]', text)

        # Extract text before and after [DRAW DIAGRAM]
        text_before = parts[0].strip()
        text_after = parts[1].strip()

        # Extract JSON string from the text after [DRAW DIAGRAM]
        json_string = re.search(r'\{.*\}', text_after, re.DOTALL)
        json_data = json.loads(json_string.group())

        # Remove JSON from the text after [DRAW DIAGRAM]
        text_after = re.sub(r'\{.*\}', '', text_after, flags=re.DOTALL).strip()

        #print("Text before [DRAW DIAGRAM]:")
        #print(text_before)
        #print("\nJSON data:")
        #print(json_data)
        #print("\nText after JSON:")
        #print(text_after)

        # draw the diagram
        diagram_image = draw_diagram(json_data)  # Uncomment this line when you have the draw_diagram function defined
        # get the summary from the json
        # text = json_data['summary'][0]['data']
        text = text_before + "\n<<DIAGRAM_HERE>>\n" + text_after
    # if the response is a websearch command, then we need to do process it
    if websearch_match:
        #query = websearch_match.group(1)
        text = chatgpt_online(socketio, text, prompt, messages, message, True)
    if webvisit_match:
        #query = webvisit_match.group(1)
        text = chatgpt_online(socketio, text, prompt, messages, message, False)
    filename = 'chat_%s_gpt3.txt' % time()
    if not os.path.exists('chat_logs'):
        os.makedirs('chat_logs')
    keywords = generate_keyword_list(prompt)
    last_keywords = keywords
    save_file('chat_logs/%s' % filename, prompt  + '\n' + str(text) + '\n\n==========\n\n')
    # save keywords to a file
    if (last_keywords is not None):
        keyfilename = 'keywords_%d.json' % int(time())
        save_file('keywords_logs/%s' % keyfilename, last_keywords)
    return text

last_keywords = load_last_recent_keywords()

def generate_keyword_list(text):
    if debug: print(white + "\ngenerating keywords for: ", text  + "\n==========================================================" + reset)
    keyword_prompt = prompt_keywords_instructions.replace('<<INPUT_TEXT>>', text)
    response = exponential_backoff(openai.ChatCompletion.create ,model=keyword_model, messages=[{"role": "system", "content": prompt_keywords_instructions},{"role": "user", "content": keyword_prompt}], temperature=0.1)
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

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/chat', methods=['POST', "OPTIONS"])
def chat():
    global diagram_image
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
    convo_length = 14
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
        output = chatgpt_completion(socketio, messages, prompt, message)
        timestamp = time()
        timestring = timestamp_to_datetime(timestamp)
        message = output
        if diagram_image is not None:
            output = output.replace('<<DIAGRAM_HERE>>', '[base64]' + diagram_image + '[/base64]')
        diagram_image = None
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
    socketio.run(app, debug=False, host='0.0.0.0', port=5001)