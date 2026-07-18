"""LangChain orchestration with LCEL chains, custom callbacks, and agent-tool-chain hierarchy.

Architecture:
  1. Cache check (short-circuit if hit)
  2. History loading from Redis
  3. Agent invocation with tool-calling (classify_intent, knowledge_retrieval, hitl_approval)
  4. Custom callbacks for structured logging
  5. Memory persistence
  6. Response caching

The chain supports:
  - Role-based RAG (user_role passed via session metadata)
  - HITL gates (agent can pause for human approval)
  - Multi-agent delegation (orchestrator routes to specialists)
"""
import time

from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from . import cache, memory
from .callbacks import StructuredLoggingCallback
from .hitl import create_approval_request, wait_for_approval
from .llm import get_llm
from .logging_utils import get_logger, log_event
from .prompt_registry import get_registry
from .tools import classify_intent, knowledge_retrieval, hitl_approval

logger = get_logger("chain")

llm = get_llm()

registry = get_registry()
system_prompt_template = registry.get("finbot_system_prompt")
few_shot_template = registry.get("few_shot_examples")

SYSTEM_PROMPT = system_prompt_template.template
for example in few_shot_template.examples:
    SYSTEM_PROMPT += f"\n    Customer: {example['input']}\n    FinBot: {example['output']}\n"

agent = create_agent(
    model=llm,
    tools=[classify_intent, knowledge_retrieval, hitl_approval],
    system_prompt=SYSTEM_PROMPT,
)


def _history_to_messages(history: list[dict]) -> list:
    messages = []
    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    return messages


# --- LCEL Chain components ---

def _check_cache(inputs: dict) -> dict:
    """Check response cache; attach cached response if found."""
    message = inputs["message"]
    cached_response = cache.get_cached_response(message)
    inputs["cached_response"] = cached_response
    return inputs


def _load_history(inputs: dict) -> dict:
    """Load session history from Redis."""
    session_id = inputs["session_id"]
    history = memory.get_history(session_id)
    inputs["history"] = history
    return inputs


def _build_messages(inputs: dict) -> dict:
    """Convert history + new message into LangChain message objects."""
    history_messages = _history_to_messages(inputs["history"])
    inputs["input_messages"] = history_messages + [HumanMessage(content=inputs["message"])]
    return inputs


def _invoke_agent(inputs: dict) -> dict:
    """Invoke the tool-calling agent with callbacks."""
    session_id = inputs["session_id"]
    callbacks = [StructuredLoggingCallback(session_id=session_id)]

    result = agent.invoke(
        {"messages": inputs["input_messages"]},
        config={
            "metadata": {
                "session_id": session_id,
                "user_role": inputs.get("user_role", "customer"),
            },
            "callbacks": callbacks,
        },
    )

    output_messages = result["messages"]
    tools_called = [
        tool_call["name"]
        for msg in output_messages
        if isinstance(msg, AIMessage)
        for tool_call in (msg.tool_calls or [])
    ]
    final_message = output_messages[-1]
    inputs["response_text"] = final_message.content
    inputs["tools_called"] = tools_called
    return inputs


def _persist_and_cache(inputs: dict) -> dict:
    """Save turn to memory and cache the response."""
    session_id = inputs["session_id"]
    message = inputs["message"]
    response_text = inputs["response_text"]

    memory.append_turn(session_id, "user", message)
    memory.append_turn(session_id, "assistant", response_text)
    cache.set_cached_response(message, response_text)
    return inputs


# Compose the LCEL chain
processing_chain = (
    RunnableLambda(_check_cache)
    | RunnableLambda(_load_history)
    | RunnableLambda(_build_messages)
    | RunnableLambda(_invoke_agent)
    | RunnableLambda(_persist_and_cache)
)


def chat(session_id: str, message: str, user_role: str = "customer") -> tuple[str, bool]:
    """Run one turn of the agent. Returns (response_text, cache_hit)."""
    start = time.monotonic()

    cached_response = cache.get_cached_response(message)
    if cached_response:
        memory.append_turn(session_id, "user", message)
        memory.append_turn(session_id, "assistant", cached_response)
        log_event(logger, "chat cache hit", session_id=session_id, customer_message=message)
        return cached_response, True

    inputs = {
        "session_id": session_id,
        "message": message,
        "user_role": user_role,
    }
    result = processing_chain.invoke(inputs)
    response_text = result["response_text"]

    log_event(
        logger,
        "chat completed",
        session_id=session_id,
        tools_called=result.get("tools_called", []),
        user_role=user_role,
        latency_ms=round((time.monotonic() - start) * 1000, 1),
    )

    return response_text, False
