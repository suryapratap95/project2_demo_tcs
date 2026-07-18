"""Prompt and embedding drift evaluation.

Detects silent degradation in:
1. Prompt effectiveness - compares current prompt outputs against baseline responses
2. Embedding quality - measures vector drift by comparing embedding consistency
   over time for fixed reference queries

Usage: python -m eval.drift_detector
"""
import json
import os
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv()

from app.llm import get_llm
from app.logging_utils import get_logger, log_event
from app.rag.embeddings import get_embeddings
from app.rag.pipeline import RAGPipeline
from eval.dataset import EVAL_DATASET
from eval.metrics import judge_answer_relevancy, judge_faithfulness

logger = get_logger("eval.drift_detector")

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
BASELINE_DIR = os.path.join(RESULTS_DIR, "baselines")

REFERENCE_QUERIES = [
    "What is the minimum balance for a savings account?",
    "How do I file a card dispute?",
    "What is the home loan interest rate?",
    "What are UPI transaction charges?",
    "How long does a NEFT transfer take?",
]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


def detect_embedding_drift(threshold: float = 0.95) -> dict:
    """Compare current embeddings against stored baseline.
    Returns drift metrics and whether drift exceeds threshold."""
    embeddings = get_embeddings()
    current_embeddings = embeddings.embed_documents(REFERENCE_QUERIES)

    baseline_path = os.path.join(BASELINE_DIR, "embedding_baseline.json")

    if not os.path.exists(baseline_path):
        os.makedirs(BASELINE_DIR, exist_ok=True)
        with open(baseline_path, "w") as f:
            json.dump({
                "queries": REFERENCE_QUERIES,
                "embeddings": current_embeddings,
                "created_at": time.time(),
            }, f)
        return {
            "status": "baseline_created",
            "message": "No baseline existed. Created new baseline for future comparison.",
            "drift_detected": False,
        }

    with open(baseline_path, "r") as f:
        baseline = json.load(f)

    similarities = []
    for i, (current, stored) in enumerate(zip(current_embeddings, baseline["embeddings"])):
        sim = _cosine_similarity(current, stored)
        similarities.append({"query": REFERENCE_QUERIES[i], "similarity": round(sim, 4)})

    avg_similarity = sum(s["similarity"] for s in similarities) / len(similarities)
    drift_detected = avg_similarity < threshold

    return {
        "status": "compared",
        "avg_similarity": round(avg_similarity, 4),
        "threshold": threshold,
        "drift_detected": drift_detected,
        "per_query": similarities,
        "baseline_created_at": baseline.get("created_at"),
    }


def detect_prompt_drift(sample_size: int = 3) -> dict:
    """Compare current prompt outputs against baseline responses.
    Measures if the same queries produce significantly different answers over time."""
    pipeline = RAGPipeline(llm=get_llm())
    baseline_path = os.path.join(BASELINE_DIR, "prompt_baseline.json")

    cases = EVAL_DATASET[:sample_size]
    current_responses = []
    for case in cases:
        answer = pipeline.answer(case["question"])
        current_responses.append({
            "question": case["question"],
            "answer": answer.answer,
            "citations": answer.citations,
        })

    if not os.path.exists(baseline_path):
        os.makedirs(BASELINE_DIR, exist_ok=True)
        with open(baseline_path, "w") as f:
            json.dump({
                "responses": current_responses,
                "created_at": time.time(),
            }, f)
        return {
            "status": "baseline_created",
            "message": "No prompt baseline existed. Created new baseline.",
            "drift_detected": False,
        }

    with open(baseline_path, "r") as f:
        baseline = json.load(f)

    comparisons = []
    for current, stored in zip(current_responses, baseline["responses"]):
        relevancy = judge_answer_relevancy(current["question"], current["answer"])
        citation_overlap = len(
            set(current["citations"]) & set(stored["citations"])
        ) / max(len(stored["citations"]), 1)

        comparisons.append({
            "question": current["question"],
            "relevancy_score": relevancy.score,
            "citation_overlap": round(citation_overlap, 2),
            "answer_changed": current["answer"] != stored["answer"],
        })

    avg_relevancy = sum(c["relevancy_score"] for c in comparisons) / len(comparisons)
    avg_citation_overlap = sum(c["citation_overlap"] for c in comparisons) / len(comparisons)
    drift_detected = avg_relevancy < 0.7 or avg_citation_overlap < 0.5

    return {
        "status": "compared",
        "avg_relevancy": round(avg_relevancy, 3),
        "avg_citation_overlap": round(avg_citation_overlap, 3),
        "drift_detected": drift_detected,
        "comparisons": comparisons,
    }


def run_drift_detection() -> dict:
    """Run full drift detection suite."""
    results = {
        "embedding_drift": detect_embedding_drift(),
        "prompt_drift": detect_prompt_drift(),
        "timestamp": time.time(),
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, f"drift_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    any_drift = results["embedding_drift"]["drift_detected"] or results["prompt_drift"]["drift_detected"]
    log_event(logger, "drift detection complete", drift_detected=any_drift, output_path=out_path)

    print("\n=== Drift Detection Results ===")
    print(f"  Embedding drift: {'DETECTED' if results['embedding_drift']['drift_detected'] else 'None'}")
    if results['embedding_drift'].get('avg_similarity'):
        print(f"    Avg similarity: {results['embedding_drift']['avg_similarity']}")
    print(f"  Prompt drift: {'DETECTED' if results['prompt_drift']['drift_detected'] else 'None'}")
    if results['prompt_drift'].get('avg_relevancy'):
        print(f"    Avg relevancy: {results['prompt_drift']['avg_relevancy']}")
    print(f"\n  Results: {out_path}\n")

    return results


if __name__ == "__main__":
    run_drift_detection()
