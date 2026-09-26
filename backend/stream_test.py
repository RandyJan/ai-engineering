import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not configured.")

client = genai.Client(api_key=api_key)

chat = client.chats.create(
    model="gemini-3.8-flash",

    config=types.GenerateContentConfig(
        system_instruction="""
        You are a helpful AI assistant.

        Explain things clearly and concisely.
        """
    ),
)

response = chat.send_message_stream(
    "Explain what FastAPI is."
)

for chunk in response:

    if chunk.text:
        print(
            chunk.text,
            end="",
            flush=True
        )