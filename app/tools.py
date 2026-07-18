import json
import re
from functools import lru_cache

from langchain_core.tools import tool
from langchain_core.callbacks import CallbackManagerForToolRun

from .llm import get_llm
from .model import IntentResult

_INTENT_RULES: list[tuple[str, list[str], str]] = [
    (
        "card_dispute",
        [
            r"charged twice", r"double charg", r"unauthoriz", r"dispute",
            r"chargeback", r"fraudulent", r"didn'?t make this (transaction|purchase)",
            r"card.*(block|stolen|lost)", r"stolen card", r"lost card",
        ],
        "card_disputes_team",
    ),
    (
        "complaint",
        [
            r"\bcomplaint\b", r"upset", r"frustrat", r"angry", r"unhappy",
            r"not resolved", r"escalate", r"worst service", r"terrible service",
            r"still waiting",
        ],
        "grievance_redressal",
    ),
    (
        "loan_query",
        [
            r"\bloan\b", r"\bemi\b", r"eligib", r"interest rate",
            r"home loan", r"personal loan", r"car loan", r"mortgage",
        ],
        "loans_team",
    ),
    (
        "account_inquiry",
        [
            r"balance", r"account statement", r"my account", r"account details",
            r"fixed deposit", r"\bfd\b", r"savings account", r"minimum balance",
        ],
        "self_service",
    ),
]

_DEFAULT_ROUTING = "general_support"


def _classify(customer_message: str) -> IntentResult:
    text = customer_message.lower()
    for intent, patterns, routing in _INTENT_RULES:
        matches = sum(1 for pattern in patterns if re.search(pattern, text))
        if matches:
            confidence = min(0.6 + 0.15 * matches, 0.98)
            return IntentResult(intent=intent, confidence=confidence, routing=routing)
    return IntentResult(intent="general_faq", confidence=0.5, routing=_DEFAULT_ROUTING)


@tool
def classify_intent(customer_message: str) -> str:
    """Deterministically classify the customer's message into a banking
    intent category using keyword rules (no LLM call, fully reproducible).

    Use this to decide how urgent/sensitive a message is or which team it
    should route to (e.g. flag card disputes and complaints for escalation).
    It does NOT answer factual questions about bank policies - use
    knowledge_retrieval for that.

    Returns a JSON string of {intent, confidence, routing} where intent is
    one of: account_inquiry | card_dispute | loan_query | complaint | general_faq.
    """
    return _classify(customer_message).model_dump_json()


@lru_cache(maxsize=1)
def _get_rag_pipeline():
    from .rag.pipeline import RAGPipeline

    return RAGPipeline(llm=get_llm())


_get_rag_pipeline()


@tool
def knowledge_retrieval(query: str) -> str:
    """Retrieve a grounded, cited answer from SecureBank's internal
    knowledge base (savings/FD terms, home loan eligibility & documents,
    card dispute policy, UPI/NEFT/RTGS/IMPS charges, general FAQs) using
    retrieval-augmented generation.

    Use this whenever the customer asks a factual question about bank
    policies, fees, charges, eligibility criteria, interest rates, or
    procedures - anything that should be answered from official
    documentation rather than from memory.

    Returns a JSON string of {answer, citations} where citations lists the
    source document filenames used to ground the answer.
    """
    rag_answer = _get_rag_pipeline().answer(query)
    return json.dumps({"answer": rag_answer.answer, "citations": rag_answer.citations})


@tool
def hitl_approval(action_type: str, description: str) -> str:
    """Request human-in-the-loop approval for a high-risk action.

    Call this when the customer requests:
    - Account closure
    - Large fund transfer (above Rs 50,000)
    - Card blocking/unblocking
    - Loan foreclosure
    - Any irreversible financial action

    The system will pause and wait for a human supervisor to approve or
    reject the action. Returns the decision result as JSON.

    Args:
        action_type: Type of action requiring approval (e.g. "account_closure", "large_transfer", "card_block")
        description: Brief description of what the customer is requesting
    """
    from .hitl import create_approval_request, wait_for_approval

    request = create_approval_request(
        session_id="current",
        action_type=action_type,
        description=description,
    )
    decision = wait_for_approval(request["request_id"], timeout=60)

    if decision["decision"] == "approved":
        return json.dumps({
            "status": "approved",
            "message": f"Action '{action_type}' has been approved by supervisor. Proceeding with: {description}",
            "approver": decision.get("approver", "supervisor"),
        })
    elif decision["decision"] == "rejected":
        return json.dumps({
            "status": "rejected",
            "message": f"Action '{action_type}' was rejected by supervisor. Reason: {decision.get('reason', 'Not specified')}",
        })
    else:
        return json.dumps({
            "status": "timeout",
            "message": "No supervisor response received within the time limit. Please try again or contact a branch representative.",
        })
