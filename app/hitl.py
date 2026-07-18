"""Human-in-the-Loop (HITL) gates.

Provides approval mechanisms for high-risk actions. The agent can pause
execution, present a recommendation, and wait for human supervisor
approval before proceeding.

Approval requests are stored in Redis with a unique ID. The frontend
or supervisor dashboard polls/receives the request and submits a
decision (approve/reject). The agent tool blocks (with timeout) until
a decision arrives.
"""
import json
import time
import uuid

from .logging_utils import get_logger, log_event
from .memory import _get_client

logger = get_logger("hitl")

HITL_TTL_SECONDS = 300  # 5 minutes to respond
HITL_POLL_INTERVAL = 2  # seconds between polls
HITL_MAX_WAIT = 120  # max seconds to block


def _hitl_key(request_id: str) -> str:
    return f"hitl:request:{request_id}"


def _hitl_response_key(request_id: str) -> str:
    return f"hitl:response:{request_id}"


def _pending_list_key(session_id: str) -> str:
    return f"hitl:pending:{session_id}"


def create_approval_request(
    session_id: str,
    action_type: str,
    description: str,
    details: dict | None = None,
) -> dict:
    """Create a new HITL approval request. Returns the request object."""
    request_id = str(uuid.uuid4())
    request = {
        "request_id": request_id,
        "session_id": session_id,
        "action_type": action_type,
        "description": description,
        "details": details or {},
        "status": "pending",
        "created_at": time.time(),
    }
    client = _get_client()
    client.set(_hitl_key(request_id), json.dumps(request), ex=HITL_TTL_SECONDS)
    client.rpush(_pending_list_key(session_id), request_id)
    client.expire(_pending_list_key(session_id), HITL_TTL_SECONDS)

    log_event(logger, "hitl request created", request_id=request_id, action_type=action_type)
    return request


def wait_for_approval(request_id: str, timeout: int = HITL_MAX_WAIT) -> dict:
    """Block until a human decision arrives or timeout. Returns decision dict."""
    client = _get_client()
    response_key = _hitl_response_key(request_id)
    elapsed = 0

    while elapsed < timeout:
        response = client.get(response_key)
        if response:
            decision = json.loads(response)
            log_event(logger, "hitl decision received", request_id=request_id, decision=decision["decision"])
            return decision
        time.sleep(HITL_POLL_INTERVAL)
        elapsed += HITL_POLL_INTERVAL

    log_event(logger, "hitl request timed out", request_id=request_id)
    return {"decision": "timeout", "reason": "No human response within timeout period"}


def submit_decision(request_id: str, decision: str, approver: str, reason: str = "") -> bool:
    """Submit a human decision for a pending HITL request."""
    client = _get_client()
    request_raw = client.get(_hitl_key(request_id))
    if not request_raw:
        return False

    response = {
        "decision": decision,  # "approved" or "rejected"
        "approver": approver,
        "reason": reason,
        "decided_at": time.time(),
    }
    client.set(_hitl_response_key(request_id), json.dumps(response), ex=HITL_TTL_SECONDS)

    request = json.loads(request_raw)
    request["status"] = decision
    client.set(_hitl_key(request_id), json.dumps(request), ex=HITL_TTL_SECONDS)

    log_event(logger, "hitl decision submitted", request_id=request_id, decision=decision, approver=approver)
    return True


def get_pending_requests(session_id: str) -> list[dict]:
    """Get all pending HITL requests for a session."""
    client = _get_client()
    request_ids = client.lrange(_pending_list_key(session_id), 0, -1)
    pending = []
    for rid in request_ids:
        raw = client.get(_hitl_key(rid))
        if raw:
            req = json.loads(raw)
            if req["status"] == "pending":
                pending.append(req)
    return pending
