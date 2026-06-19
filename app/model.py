from pydantic import BaseModel, Field

class IntentResult(BaseModel):
    intent: str = Field(description="account_inquiry | card_dispute | loan_query | complaint | general_faq")
    confidence: float = Field(ge=0, le=1)
    routing: str

class ChatRequest(BaseModel):
    message:str = Field(...,min_lengt=1, max_lengt=2000, description="customer message")
    session_id: str = Field(default="default",description="session identifier")
    
    
class ChatResponse(BaseModel):
    response: str
    session_id: str
    cached: bool = False