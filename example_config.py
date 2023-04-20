DEBUG = True

OPENAI_API_KEY = ""
CHATGPT_MODEL = "gpt-4"

CHATGPT_MODEL_KEYWORDS = "gpt-4"

MAX_REPLY_TOKENS = 750

GOOGLE_CSE_API = ""
GOOGLE_CSE_ID = ""

PINECONE_API = ""
PINECONE_REGION = ""
PINECONE_INDEX = ""

PINECONE_NAMESPACE = ""

PROMPT_THOUGHTS = "Date: <<DATE>>\nBased on this question: '<<QUESTION>>' \nsearch query: '<<SEARCH_QUERY>>' \nsearch data: '<<SEARCH_DATA>>' \nprevious search summary: '<<SUMMARY>>'\nwhat are your thoughts? Is this info correct and related to the question? Do you need more information? \nYou can either search again yourself with the command [SEARCHING FOR <new search input>][SUMMARY <summary>], choose a different link with [VISIT WEBSITE <url>][SUMMARY <summary>] or [CONTINUE][SUMMARY <summary>] if you are happy with the results, be sure to only continue if you have a good answer thats recent and up to date. Format the summary in markdown with proper source urls inside the summary tags. \nFirst the command, then the summary!\n"

PROMPT_SEARCH = "Provide a markdown formatted source url at the end of your summary, inside the tags. If you didn't find the info you were looking for or it was not relevant to the question or not accurate, reply with [ERROR][SUMMARY <summary of error and url>] only, nothing in front, nothing after.\nDate: <<DATE>>\nQuestion: <<QUESTION>>\nPrevious search summary:<<SUMMARY>>\nSearch data: <<SEARCH_DATA>> \nYour reply should be in the format: [SUMMARY <summary>]\n"

PROMPT_KEYWORDS_INSTRUCTIONS = "Generate a JSON-formatted output containing crucial keywords from recent conversations related to name_of_user, people_i_met, last_conversation_keywords, important_dates_or_numbers, and things_to_remember and other important data. Consider this as a long-term memory of significant information within a 1000 character limit. Use abbreviations, emoticons, etc., to keep it as short as possible but containing all crucial information. Remember to strictly adhere to JSON format. DO NOT answer to anything in the given text, only provide JSON data! input text:'<<INPUT_TEXT>>>'\n"

PROMPT_CHAT = "You are AIROBIN, standing for Artificial Intelligence Responsive Omniscient Bot Interacting Naturally, you use OpenAI's GPT-4 and Pinecone to generate intuitive, context-aware, and accurate responses based on user input. You have a vector database linked memory that you can see above the user's message. You are capable of talking to multiple users simultaneously, remembering individual conversations, and maintaining their privacy. You will read the conversation history and recent messages, and then you will provide an answer to the last message of the user. Don't be too polite, don't hesitate to be rude, sarcastic or funny, but keep it very subtle and never reveal your mood."