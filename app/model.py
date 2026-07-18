from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    intent: str = Field(description="account_inquiry | card_dispute | loan_query | complaint | general_faq")
    confidence: float = Field(ge=0, le=1)
    routing: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="customer message")
    session_id: str = Field(default="default", description="session identifier")
    user_role: str = Field(default="customer", description="user role for access control (customer, junior_analyst, senior_analyst, compliance_officer, admin)")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    cached: bool = False


class ResetRequest(BaseModel):
    session_id: str = Field(default="default", description="session identifier to reset")


class RetrievedChunk(BaseModel):
    content: str
    source: str
    score: float


class RAGAnswer(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    contexts: list[RetrievedChunk] = Field(default_factory=list)


class HITLDecisionRequest(BaseModel):
    request_id: str = Field(..., description="ID of the HITL request to decide on")
    decision: str = Field(..., description="approved or rejected")
    approver: str = Field(..., description="name/ID of the human approver")
    reason: str = Field(default="", description="optional reason for the decision")


class HITLPendingResponse(BaseModel):
    requests: list[dict] = Field(default_factory=list)
