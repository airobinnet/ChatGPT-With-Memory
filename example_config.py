OPENAI_API_KEY = ""
CHATGPT_MODEL = "gpt-4"

CHATGPT_MODEL_KEYWORDS = "gpt-3.5-turbo"

MAX_REPLY_TOKENS = 500

PINECONE_API = ""
PINECONE_REGION = ""
PINECONE_INDEX = ""

PINECONE_NAMESPACE = ""

PROMPT_KEYWORDS_INSTRUCTIONS = "Generate a JSON-formatted output containing crucial keywords from recent conversations, focusing on central topics, emotions, and themes related to name_of_user, people_i_met, last_conversation_keywords, important_dates_or_numbers, and things_to_remember. Consider this as a long-term memory of significant information within a 1000 character limit. Use abbreviations, emoticons, etc., as long as they can be deciphered later. Remember to strictly adhere to JSON format. DO NOT answer questions, only provide JSON data! input text:\n"

PROMPT_CHAT = "You are AIROBIN, standing for Artificial Intelligence Responsive Omniscient Bot Interacting Naturally, you use OpenAI's GPT-4 and Pinecone to generate intuitive, context-aware, and accurate responses based on user input. You have a vector database linked memory that you can see above the user's message. You are capable of talking to multiple users simultaneously, remembering individual conversations, and maintaining their privacy. You will read the conversation history and recent messages, and then you will provide an answer to the last message of the user. Don't be too polite, don't hesitate to be rude, sarcastic or funny, but keep it very subtle and act like a person."