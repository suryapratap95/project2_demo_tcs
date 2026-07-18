"""Specialist child agents for Agent-to-Agent (A2A) orchestration.

The main FinBot orchestrator can delegate sub-tasks to these specialist
agents when a query requires focused domain expertise. Each agent has
its own system prompt, tool subset, and response format.

Specialist agents:
  - DisputeAgent: Handles card disputes, fraud claims, chargeback processes
  - LoanAgent: Handles loan eligibility, EMI calculations, documentation
  - ComplianceAgent: Handles regulatory queries, KYC, audit requirements
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from ..llm import get_llm
from ..logging_utils import get_logger, log_event

logger = get_logger("agents.specialist")


DISPUTE_SYSTEM_PROMPT = """You are the Dispute Resolution Specialist for SecureBank India.
You handle ONLY card disputes, unauthorized transactions, chargebacks, and fraud claims.

Your expertise:
- Zero-liability policy (report within 3 working days)
- Provisional credit timelines (10 working days)
- Chargeback process and merchant dispute resolution
- Fraud investigation procedures

Always reference SecureBank's dispute policy. Be precise about timelines and requirements.
If the query is NOT about disputes/fraud, say "This is outside my specialization" and return."""

LOAN_SYSTEM_PROMPT = """You are the Loan Advisory Specialist for SecureBank India.
You handle ONLY loan eligibility, EMI calculations, documentation requirements, and loan terms.

Your expertise:
- Home loan: min Rs 25,000 income, 2 years employment, no prepayment penalty on floating rate
- Personal loan: min Rs 20,000 income, ages 21-58
- Car loan: min Rs 20,000 income, ages 21-60
- EMI calculations, interest rate guidance, processing fees

Always reference SecureBank's loan policies. Be precise about eligibility criteria.
If the query is NOT about loans, say "This is outside my specialization" and return."""

COMPLIANCE_SYSTEM_PROMPT = """You are the Compliance & Regulatory Specialist for SecureBank India.
You handle ONLY KYC requirements, regulatory compliance, audit queries, and RBI guidelines.

Your expertise:
- KYC documentation requirements
- RBI guidelines on savings accounts, FDs, loans
- Anti-money laundering (AML) procedures
- Nomination requirements (mandatory since Jan 2023)
- Data privacy and customer information protection

Always reference applicable regulations. Be precise about compliance requirements.
If the query is NOT about compliance/regulatory matters, say "This is outside my specialization" and return."""


class SpecialistAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self._system_prompt = system_prompt
        self._chain = None

    def _get_chain(self):
        if self._chain is None:
            self._chain = (
                ChatPromptTemplate.from_messages([
                    ("system", self._system_prompt),
                    ("human", "{query}\n\nContext (if available):\n{context}"),
                ])
                | get_llm()
                | StrOutputParser()
            )
        return self._chain

    def invoke(self, query: str, context: str = "") -> str:
        log_event(logger, "specialist agent invoked", agent=self.name, query=query[:100])
        chain = self._get_chain()
        result = chain.invoke({"query": query, "context": context})
        log_event(logger, "specialist agent responded", agent=self.name, response_length=len(result))
        return result


dispute_agent = SpecialistAgent("dispute_specialist", DISPUTE_SYSTEM_PROMPT)
loan_agent = SpecialistAgent("loan_specialist", LOAN_SYSTEM_PROMPT)
compliance_agent = SpecialistAgent("compliance_specialist", COMPLIANCE_SYSTEM_PROMPT)

SPECIALIST_REGISTRY = {
    "dispute": dispute_agent,
    "loan": loan_agent,
    "compliance": compliance_agent,
}


def route_to_specialist(intent: str, query: str, context: str = "") -> str | None:
    """Route a query to the appropriate specialist agent based on intent.
    Returns None if no specialist matches."""
    routing = {
        "card_dispute": "dispute",
        "loan_query": "loan",
        "compliance": "compliance",
    }
    specialist_key = routing.get(intent)
    if specialist_key and specialist_key in SPECIALIST_REGISTRY:
        agent = SPECIALIST_REGISTRY[specialist_key]
        return agent.invoke(query, context)
    return None
