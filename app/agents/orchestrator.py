"""Multi-agent orchestrator.

The orchestrator agent decides whether to handle a query directly or
delegate to a specialist child agent. It coordinates between agents
and synthesizes responses when multiple specialists are consulted.
"""
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ..llm import get_llm
from ..logging_utils import get_logger, log_event
from .specialist_agents import SPECIALIST_REGISTRY, route_to_specialist

logger = get_logger("agents.orchestrator")

ORCHESTRATOR_PROMPT = """You are the routing orchestrator for SecureBank India's AI system.
Given a customer query and its classified intent, decide whether to:
1. Handle it directly (for simple greetings, general info)
2. Delegate to a specialist agent (for domain-specific queries)
3. Consult multiple specialists (for complex queries spanning domains)

Available specialists: {specialists}

Customer query: {query}
Classified intent: {intent}
Confidence: {confidence}

Respond with a JSON object:
{{"action": "direct|delegate|multi", "specialists": ["list of specialist keys to consult"], "reason": "brief explanation"}}"""


class AgentOrchestrator:
    def __init__(self):
        self._llm = get_llm()
        self._routing_chain = (
            ChatPromptTemplate.from_messages([
                ("system", ORCHESTRATOR_PROMPT),
            ])
            | self._llm
            | StrOutputParser()
        )

    def route(self, query: str, intent: str, confidence: float) -> dict:
        """Decide routing based on query and intent."""
        specialists_desc = ", ".join(
            f"{k} ({v.name})" for k, v in SPECIALIST_REGISTRY.items()
        )
        result = self._routing_chain.invoke({
            "query": query,
            "intent": intent,
            "confidence": confidence,
            "specialists": specialists_desc,
        })
        try:
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            return {"action": "direct", "specialists": [], "reason": "fallback"}

    def execute(self, query: str, intent: str, confidence: float, context: str = "") -> dict:
        """Route and execute the query through appropriate agent(s)."""
        routing = self.route(query, intent, confidence)
        log_event(logger, "orchestrator routing decision",
                  query=query[:100], intent=intent, action=routing["action"])

        if routing["action"] == "direct":
            return {"handled_by": "main_agent", "specialist_response": None, "routing": routing}

        responses = {}
        for specialist_key in routing.get("specialists", []):
            response = route_to_specialist(specialist_key, query, context)
            if response:
                responses[specialist_key] = response

        if not responses:
            return {"handled_by": "main_agent", "specialist_response": None, "routing": routing}

        combined = "\n\n".join(f"[{k}]: {v}" for k, v in responses.items())
        return {
            "handled_by": "specialist",
            "specialist_response": combined,
            "individual_responses": responses,
            "routing": routing,
        }
