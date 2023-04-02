# AIROBIN Chatbot

This is a README for the AIROBIN chatbot script. The AIROBIN chatbot, standing for Artificial Intelligence Responsive Omniscient Bot Interacting Naturally, is a conversational AI that uses OpenAI's GPT-4 or GPT-3.5-turbo and Pinecone to generate intuitive, context-aware, and accurate responses based on user input. It harnesses the power of Pinecone's managed vector database service to provide a nearly infinite extended memory for conversational context, enabling sophisticated and seamless interactions.

## Dependencies

- OpenAI API
- Pinecone API
- numpy
- Flask
- Flask-CORS

## How it works

1. The script initializes the OpenAI and Pinecone APIs using the provided API keys.
2. It loads the last recent keywords from the `keywords_logs` directory if they exist.
3. The main loop starts, where it takes user input, saves it, vectorizes it, and saves it to Pinecone.
4. It searches for relevant messages and generates a response based on the conversation utilizing advanced natural language understanding and processing techniques.
5. The response is generated using GPT-4 or GPT-3.5-turbo, vectorized, saved, and added to Pinecone, ensuring optimal information retrieval and context awareness.
6. The chatbot's response is displayed to the user, providing a seamless conversational experience.

## Requirements
1. OpenAI API
2. Pinecone API

## Usage

1. Rename `example_config.py` to `config.py` and set up your OpenAI and Pinecone API keys.
2. In `config.py` choose the models you want to use `gpt-3.5-turbo` or `gpt-4`.
3. Install the required dependencies using `pip install openai pinecone numpy flask flask-cors`.
4. Run the script using `python main.py`.
5. Open the `web/index.html` file in your browser to interact with the chatbot.

## Files and directories

- `config.py`: Contains the API keys and other configurations.
- `main.py`: The main script for the AIROBIN chatbot.
- `web/index.html`: The web interface for interacting with the chatbot.
- `chat_logs`: Directory containing chat logs saved as text files.
- `keywords_logs`: Directory containing keyword logs saved as JSON files.
- `messages`: Directory containing message metadata saved as JSON files.
- `prompt_response.txt`: Template for generating the prompt for GPT.

## Note
A substantial amount of credit goes to https://github.com/daveshap/PineconeInfiniteMemoryChatbot for contributing major portions of the code.
This README presumes that you have already established your OpenAI and Pinecone accounts and possess the required API keys. 
GPT-4 is slower yet significantly more intelligent than GPT3-5-turbo. If your budget allows, opt for the gpt-4 model, as it is more advanced. 
