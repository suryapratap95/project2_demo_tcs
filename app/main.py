from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from .chain import chat
from . import memory
from .model import ChatRequest, ChatResponse, ResetRequest

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
        response_text, cached = chat(session_id=req.session_id, message=req.message)
        return ChatResponse(session_id=req.session_id, response=response_text, cached=cached)
    except Exception as exc :
        raise HTTPException(
        status_code=500,
        detail=str(exc)
    )


@app.post("/reset")
def reset_endpoint(req: ResetRequest) -> bool :
    memory.clear_session(req.session_id)
    return True


@app.get("/health")
def health_endpoint() -> dict:
    checks = {}

    try:
        from .rag.vectorstore import get_vectorstore
        collection_count = len(get_vectorstore().get()["ids"])
        checks["vectorstore"] = {"ok": True, "chunk_count": collection_count}
    except Exception as exc:
        checks["vectorstore"] = {"ok": False, "error": str(exc)}

    try:
        memory._get_client().ping()
        checks["redis"] = {"ok": True}
    except Exception as exc:
        checks["redis"] = {"ok": False, "error": str(exc)}

    checks["openai_api_key_configured"] = bool(os.getenv("OPENAI_API_KEY"))

    status = "ok" if checks["vectorstore"]["ok"] and checks["redis"]["ok"] else "degraded"
    return {"status": status, "checks": checks}
