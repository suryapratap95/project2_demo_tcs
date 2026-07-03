from pydantic import BaseModel, Field

class IntentResult(BaseModel):
    intent: str = Field(description="account_inquiry | card_dispute | loan_query | complaint | general_faq")
    confidence: float = Field(ge=0, le=1)
    routing: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="customer message")
    session_id: str = Field(default="default", description="session identifier")


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
