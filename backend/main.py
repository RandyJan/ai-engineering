import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import errors, types
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
from groq import Groq



load_dotenv()

gemini_client = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")
if not gemini_client:
    raise ValueError("GEMINI_API_KEY is not configured.")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not configured.")

gemini_client = genai.Client(api_key=gemini_client)

groq_client = Groq(
    api_key=groq_api_key
)

app = FastAPI(
    title="LLM Learning API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary in-memory storage
conversations = {}
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)
SYSTEM_INSTRUCTION = """
You are an AI assistant for an employee management system.

Rules:
- Keep answers clear and professional.
- Never invent employee information.
- If information is unavailable, clearly say so.
"""


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    provider: Literal["gemini", "groq"] = "groq"

class ChatResponse(BaseModel):
    answer: str

class EmployeeExtractionRequest(BaseModel):
    text: str
    
class EmployeeData(BaseModel):
    employee_id: str | None = None
    name: str | None = None
    position: str | None = None
    department: str | None = None

@app.get("/")
def root():
    return {
        "message": "LLM Learning API is running"
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):

    try:

        # Create conversation if it doesn't exist
        if request.conversation_id not in conversations:

            conversations[request.conversation_id] = gemini_client.chats.create(
                model="gemini-3.8-flash",
             

                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=200,

                    system_instruction="""
                    You are an AI assistant for an employee management system.

                    Rules:
                    - Keep answers concise and professional.
                    - Never invent employee information.
                    - If information is unavailable, clearly say so.
                    """
                ),
            )

        # Get existing conversation
        chat = conversations[request.conversation_id]

        # Send message
        response = chat.send_message(
            request.message
        )

        return ChatResponse(
            answer=response.text
        )

    except errors.APIError as error:

        raise HTTPException(
            status_code=503,
            detail=f"Gemini API error: {error}"
        )
@app.post(
    "/api/extract-employee",
    response_model=EmployeeData
)
def extract_employee(request: EmployeeExtractionRequest):


    try:

        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",

            contents=request.text,

            config=types.GenerateContentConfig(
                temperature=0.1,

                system_instruction="""
                Extract employee information from the provided text.

                Rules:
                - Never invent information.
                - If information is missing, return null.
                """,

                response_mime_type="application/json",

                response_schema=EmployeeData,
            ),
        )

        return EmployeeData.model_validate_json(
            response.text
        )

    except errors.ClientError as error:

        if error.code == 429:
            raise HTTPException(
                status_code=429,
                detail="LLM rate limit reached. Please try again later."
            )

        raise HTTPException(
            status_code=400,
            detail=f"Gemini API error: {error}"
        )

    except errors.ServerError:


        raise HTTPException(

            status_code=503,
            detail="The LLM service is temporarily unavailable."
        )
@app.post("/api/chat/stream") 
def chat_stream(request: ChatRequest):

    def generate():

        yield from stream_llm(
            provider=request.provider,
            message=request.message,
        )

    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )
def stream_llm(
    provider: str,
    message: str,
):
    if provider == "gemini":
        yield from stream_gemini(message)

    elif provider == "groq":
        yield from stream_groq(message)

    else:
        yield "[Unsupported LLM provider.]"
def stream_groq(message: str):
    try:
        print(f"Starting Groq stream using {GROQ_MODEL}...")

        stream = groq_client.chat.completions.create(
             model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            stream=True,
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content

            if content:
                print("GROQ CHUNK:", repr(content))
                yield content

        print("Groq stream completed.")

    except Exception as error:
        print("GROQ ERROR:", repr(error))
        yield f"\n[Groq error: {str(error)}]"
    # try:
    #     print("Starting Groq stream...")

    #     stream = groq_client.chat.completions.create(
    #             model="qwen/qwen3.8-27b",
    #         messages=[
    #             {
    #                 "role": "system",
    #                 "content": SYSTEM_INSTRUCTION,
    #             },
    #             {
    #                 "role": "user",
    #                 "content": message,
    #             },
    #         ],
    #         stream=True,
    #     )

    #     for chunk in stream:
    #         content = chunk.choices[0].delta.content

    #         if content:
    #             print("GROQ CHUNK:", repr(content))
    #             yield content

    #     print("Groq stream completed.")

    except Exception as error:
        print("GROQ ERROR TYPE:", type(error).__name__)
        print("GROQ ERROR:", repr(error))

        yield f"\n[Groq error: {str(error)}]"

    except Exception as error:
        print("Groq error:", repr(error))
        yield "\n[Groq is currently unavailable.]"
def stream_gemini(message: str):
    try:
        response = gemini_client.models.generate_content_stream(
            model="gemini-3.8-flash",
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            ),
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as error:
        print("Gemini error:", repr(error))
        yield "\n[Gemini is currently unavailable.]"
        