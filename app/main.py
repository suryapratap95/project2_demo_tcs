from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from .chain import chat
from . import memory
from .hitl import get_pending_requests, submit_decision
from .model import ChatRequest, ChatResponse, ResetRequest, HITLDecisionRequest, HITLPendingResponse
from .prompt_registry import get_registry

load_dotenv()

app = FastAPI(
    title="FinBot - SecureBank AI Assistant",
    description="LangChain-powered banking assistant with RAG, HITL gates, role-based access, and MCP integration",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    try:
        response_text, cached = chat(
            session_id=req.session_id,
            message=req.message,
            user_role=req.user_role,
        )
        return ChatResponse(session_id=req.session_id, response=response_text, cached=cached)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/reset")
def reset_endpoint(req: ResetRequest) -> bool:
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

    try:
        registry = get_registry()
        checks["prompt_registry"] = {"ok": True, "prompts_loaded": len(registry.list_all())}
    except Exception as exc:
        checks["prompt_registry"] = {"ok": False, "error": str(exc)}

    status = "ok" if checks["vectorstore"]["ok"] and checks["redis"]["ok"] else "degraded"
    return {"status": status, "checks": checks}


# --- HITL Endpoints ---

@app.get("/hitl/pending/{session_id}")
def hitl_pending_endpoint(session_id: str) -> HITLPendingResponse:
    """Get pending HITL approval requests for a session."""
    pending = get_pending_requests(session_id)
    return HITLPendingResponse(requests=pending)


@app.post("/hitl/decide")
def hitl_decide_endpoint(req: HITLDecisionRequest) -> dict:
    """Submit a human decision for a pending HITL request."""
    success = submit_decision(
        request_id=req.request_id,
        decision=req.decision,
        approver=req.approver,
        reason=req.reason,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or expired")
    return {"status": "accepted", "request_id": req.request_id, "decision": req.decision}


# --- Prompt Management Endpoints ---

@app.get("/prompts")
def list_prompts_endpoint() -> list[dict]:
    """List all version-controlled prompt templates."""
    registry = get_registry()
    return registry.list_all()


@app.get("/prompts/{name}")
def get_prompt_endpoint(name: str) -> dict:
    """Get a specific prompt template by name."""
    registry = get_registry()
    try:
        prompt = registry.get(name)
        return {
            **prompt.get_metadata(),
            "template": prompt.template or prompt.system_template,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/prompts/reload")
def reload_prompts_endpoint() -> dict:
    """Reload all prompts from YAML files (hot-reload without restart)."""
    registry = get_registry()
    registry.reload()
    return {"status": "reloaded", "count": len(registry.list_all())}
