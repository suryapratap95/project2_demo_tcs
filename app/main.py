from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from .chain import chat
from .model import ChatRequest, ChatResponse

load_dotenv()

app = FastAPI(
    title="Smart Assitant Bot for secure Bank",
    description ="Langchain powered description smart bot for memeory, cache and structured outpui"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
def chat_endpoint(req: ChatRequest) :
    try:
        result = chat(session_id=req.session_id, message=req.message)
        return ChatResponse(session_id=req.session_id, response=result)
    except Exception as exc :
        raise HTTPException(
        status_code=500,
        detail=str(exc)
    )


@app.post("/reset")
def reset_endpoint() -> bool :
    return True