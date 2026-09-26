import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import errors, types
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not configured.")

client = genai.Client(api_key=api_key)

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


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


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

            conversations[request.conversation_id] = client.chats.create(
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

        response = client.models.generate_content(
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

    if request.conversation_id not in conversations:

        conversations[request.conversation_id] = client.chats.create(
            model="gemini-3.8-flash",

            config=types.GenerateContentConfig(
                system_instruction="""
                You are an AI assistant for an employee management system.

                Rules:
                - Keep answers clear and professional.
                - Never invent employee information.
                - If information is unavailable, clearly say so.
                """
            ),
        )

    chat = conversations[request.conversation_id]

    def generate():

        response = chat.send_message_stream(
            request.message
        )

        for chunk in response:

            if chunk.text:
                yield chunk.text

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )