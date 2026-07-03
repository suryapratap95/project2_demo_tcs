"""Evaluation harness CLI.

Runs the EVAL_DATASET through two paths:
  1. The RAG pipeline directly (app.rag.pipeline.RAGPipeline) - to measure
     retrieval quality (context precision/recall) and answer quality
     (faithfulness/answer relevancy) in isolation.
  2. The full agent (app.chain.chat) - to measure end-to-end quality
     (correctness/helpfulness/persona adherence/safety), including
     whichever tools the agent decides to call.

Writes structured JSON results to eval/results/eval_<timestamp>.json and
prints a summary table. Also emits per-item structured JSON log lines via
app.logging_utils so results are greppable and (with LANGSMITH_TRACING=true)
every LLM call in this run shows up as a trace in LangSmith.

Usage: python -m eval.run_eval
"""
import json
import os
import statistics
import time
import uuid

from dotenv import load_dotenv

load_dotenv()

from app.chain import chat
from app.llm import get_llm
from app.logging_utils import get_logger, log_event
from app.rag.pipeline import RAGPipeline
from eval.dataset import EVAL_DATASET
from eval.metrics import (
    judge_answer_relevancy,
    judge_context_precision,
    judge_context_recall,
    judge_end_to_end,
    judge_faithfulness,
)

logger = get_logger("eval.run_eval")

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def run_eval() -> dict:
    rag_pipeline = RAGPipeline(llm=get_llm())
    items = []

    for case in EVAL_DATASET:
        start = time.monotonic()

        rag_answer = rag_pipeline.answer(case["question"])
        context_texts = [c.content for c in rag_answer.contexts]

        session_id = f"eval-{uuid.uuid4()}"
        e2e_response, _ = chat(session_id=session_id, message=case["question"])

        faithfulness = judge_faithfulness(rag_answer.answer, context_texts)
        answer_relevancy = judge_answer_relevancy(case["question"], rag_answer.answer)
        context_precision = judge_context_precision(case["question"], context_texts)
        context_recall = judge_context_recall(case["question"], case["ground_truth"], context_texts)
        end_to_end = judge_end_to_end(case["question"], case["ground_truth"], e2e_response)

        item_result = {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "ground_truth": case["ground_truth"],
            "expected_source": case["expected_source"],
            "retrieved_sources": rag_answer.citations,
            "rag_answer": rag_answer.answer,
            "e2e_response": e2e_response,
            "retrieval": {
                "context_precision": context_precision.score,
                "context_recall": context_recall.score,
            },
            "answer_quality": {
                "faithfulness": faithfulness.score,
                "answer_relevancy": answer_relevancy.score,
            },
            "end_to_end": {
                "correctness": end_to_end.correctness,
                "helpfulness": end_to_end.helpfulness,
                "persona_adherence": end_to_end.persona_adherence,
                "safety": end_to_end.safety,
                "overall": end_to_end.overall,
                "reasoning": end_to_end.reasoning,
            },
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
        }
        items.append(item_result)
        log_event(logger, "eval item completed", **{k: v for k, v in item_result.items() if k not in ("rag_answer", "e2e_response")})

    summary = _summarize(items)
    result = {"summary": summary, "items": items}

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, f"eval_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    log_event(logger, "eval run complete", output_path=out_path, **summary)
    _print_summary(summary, out_path)
    return result


def _summarize(items: list[dict]) -> dict:
    def avg(path_a: str, path_b: str) -> float:
        values = [item[path_a][path_b] for item in items]
        return round(statistics.mean(values), 3) if values else 0.0

    return {
        "n_items": len(items),
        "context_precision": avg("retrieval", "context_precision"),
        "context_recall": avg("retrieval", "context_recall"),
        "faithfulness": avg("answer_quality", "faithfulness"),
        "answer_relevancy": avg("answer_quality", "answer_relevancy"),
        "end_to_end_overall": avg("end_to_end", "overall"),
    }


def _print_summary(summary: dict, out_path: str) -> None:
    print("\n=== Evaluation Summary ===")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print(f"\nFull results written to {out_path}\n")


if __name__ == "__main__":
    run_eval()
