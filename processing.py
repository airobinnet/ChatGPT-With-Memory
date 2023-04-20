import os
import json
import datetime
import glob
import re
import config
from ansicolors import red, green, yellow, blue, magenta, cyan, white, reset

debug = config.DEBUG

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

def load_last_recent_keywords():
    keywords_dir = 'keywords_logs'
    if not os.path.exists(keywords_dir):
        return []

    files = [os.path.join(keywords_dir, f) for f in os.listdir(keywords_dir) if os.path.isfile(os.path.join(keywords_dir, f))]
    if not files:
        return []

    latest_file = max(files, key=os.path.getctime)
    return json.loads(open_file(latest_file))


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