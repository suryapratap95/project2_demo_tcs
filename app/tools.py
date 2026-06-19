from langchain_core.tools import tool
from .model import IntentResult

@tool
def classify_intent(customer_message: str) -> str:
    """
    classify te customer intent as per te message.
    always take input as customer question 
    return in the JSON format 
class IntentResult(BaseModel):
    intent: str = Field(description="account_inquiry | card_dispute | loan_query | complaint | general_faq")
    confidence: float = Field(ge=0, le=1)
    routing: str
    """

# print(classify_intent.name)
# print(classify_intent.description)
# print(classify_intent.invoke({"customer_message": "i get invalid fees charge on my card"}))
