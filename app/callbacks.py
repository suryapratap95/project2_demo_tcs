"""Custom LangChain callbacks for structured observability.

Provides callbacks that hook into the LangChain execution lifecycle
(chain start/end, tool start/end, LLM start/end) and emit structured
JSON log events. Integrates with the existing logging_utils module.
"""
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from .logging_utils import get_logger, log_event

logger = get_logger("callbacks")


class StructuredLoggingCallback(BaseCallbackHandler):
    """Emits structured JSON logs for every LangChain lifecycle event."""

    def __init__(self, session_id: str = "unknown"):
        super().__init__()
        self.session_id = session_id
        self._timers: dict[str, float] = {}

    def on_chain_start(self, serialized: dict | None, inputs: dict, *, run_id: UUID, **kwargs) -> None:
        self._timers[str(run_id)] = time.monotonic()
        log_event(logger, "chain started",
                  session_id=self.session_id,
                  chain_name=(serialized or {}).get("name", "unknown"),
                  run_id=str(run_id))

    def on_chain_end(self, outputs: dict, *, run_id: UUID, **kwargs) -> None:
        elapsed = time.monotonic() - self._timers.pop(str(run_id), time.monotonic())
        log_event(logger, "chain ended",
                  session_id=self.session_id,
                  run_id=str(run_id),
                  latency_ms=round(elapsed * 1000, 1))

    def on_tool_start(self, serialized: dict | None, input_str: str, *, run_id: UUID, **kwargs) -> None:
        self._timers[str(run_id)] = time.monotonic()
        log_event(logger, "tool started",
                  session_id=self.session_id,
                  tool_name=(serialized or {}).get("name", "unknown"),
                  run_id=str(run_id))

    def on_tool_end(self, output: str, *, run_id: UUID, **kwargs) -> None:
        elapsed = time.monotonic() - self._timers.pop(str(run_id), time.monotonic())
        log_event(logger, "tool ended",
                  session_id=self.session_id,
                  run_id=str(run_id),
                  latency_ms=round(elapsed * 1000, 1),
                  output_length=len(output) if output else 0)

    def on_llm_start(self, serialized: dict | None, prompts: list[str], *, run_id: UUID, **kwargs) -> None:
        self._timers[str(run_id)] = time.monotonic()
        log_event(logger, "llm started",
                  session_id=self.session_id,
                  model=(serialized or {}).get("kwargs", {}).get("model_name", "unknown"),
                  run_id=str(run_id))

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs) -> None:
        elapsed = time.monotonic() - self._timers.pop(str(run_id), time.monotonic())
        token_usage = {}
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
        log_event(logger, "llm ended",
                  session_id=self.session_id,
                  run_id=str(run_id),
                  latency_ms=round(elapsed * 1000, 1),
                  token_usage=token_usage)

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs) -> None:
        log_event(logger, "chain error",
                  session_id=self.session_id,
                  run_id=str(run_id),
                  error=str(error))

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs) -> None:
        log_event(logger, "tool error",
                  session_id=self.session_id,
                  run_id=str(run_id),
                  error=str(error))


class HITLGateCallback(BaseCallbackHandler):
    """Callback that intercepts tool calls requiring human approval."""

    def __init__(self, session_id: str = "unknown"):
        super().__init__()
        self.session_id = session_id
        self.approval_results: dict[str, dict] = {}

    def on_tool_start(self, serialized: dict, input_str: str, *, run_id: UUID, **kwargs) -> None:
        tool_name = serialized.get("name", "")
        if tool_name == "hitl_approval":
            log_event(logger, "hitl gate triggered",
                      session_id=self.session_id,
                      tool_name=tool_name,
                      run_id=str(run_id))
