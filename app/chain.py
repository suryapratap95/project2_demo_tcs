import time

from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from . import cache, memory
from .llm import get_llm
from .logging_utils import get_logger, log_event
from .prompts import SYSTEM_PROMT
from .tools import classify_intent, knowledge_retrieval

logger = get_logger("chain")

llm = get_llm()

agent = create_agent(
    model=llm,
    tools=[classify_intent, knowledge_retrieval],
    system_prompt=SYSTEM_PROMT,
)


def _history_to_messages(history: list[dict]) -> list:
    messages = []
    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    return messages


def chat(session_id: str, message: str) -> tuple[str, bool]:
    """Run one turn of the agent. Returns (response_text, cache_hit)."""
    start = time.monotonic()

    cached_response = cache.get_cached_response(message)
    if cached_response:
        memory.append_turn(session_id, "user", message)
        memory.append_turn(session_id, "assistant", cached_response)
        log_event(logger, "chat cache hit", session_id=session_id, customer_message=message)
        return cached_response, True

    history = memory.get_history(session_id)
    input_messages = _history_to_messages(history) + [HumanMessage(content=message)]

    result = agent.invoke(
        {"messages": input_messages},
        config={"metadata": {"session_id": session_id}},
    )

    output_messages = result["messages"]
    tools_called = [
        tool_call["name"]
        for msg in output_messages
        if isinstance(msg, AIMessage)
        for tool_call in (msg.tool_calls or [])
    ]
    final_message = output_messages[-1]
    response_text = final_message.content

    memory.append_turn(session_id, "user", message)
    memory.append_turn(session_id, "assistant", response_text)
    cache.set_cached_response(message, response_text)

    log_event(
        logger,
        "chat completed",
        session_id=session_id,
        tools_called=tools_called,
        latency_ms=round((time.monotonic() - start) * 1000, 1),
    )

    return response_text, False
