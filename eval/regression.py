"""Automated regression test suite for RAG quality.

Runs against a fixed dataset and compares scores to established baselines.
If any metric drops below its threshold, the test fails — catching silent
degradation before it reaches production.

Usage: python -m eval.regression
"""
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

from app.llm import get_llm
from app.logging_utils import get_logger, log_event
from app.rag.pipeline import RAGPipeline
from eval.dataset import EVAL_DATASET
from eval.metrics import (
    judge_answer_relevancy,
    judge_context_precision,
    judge_context_recall,
    judge_faithfulness,
)

logger = get_logger("eval.regression")

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

BASELINE_THRESHOLDS = {
    "context_precision": 0.6,
    "context_recall": 0.6,
    "faithfulness": 0.7,
    "answer_relevancy": 0.7,
}

ROLE_TEST_CASES = [
    {
        "role": "customer",
        "query": "What is the minimum balance for savings account?",
        "should_access": ["faq_general.html", "savings_account_faq.html"],
        "should_not_access": ["card_dispute_policy.pdf"],
    },
    {
        "role": "junior_analyst",
        "query": "What documents are needed for home loan?",
        "should_access": ["home_loan_policy.docx", "faq_general.html"],
        "should_not_access": ["card_dispute_policy.pdf"],
    },
    {
        "role": "senior_analyst",
        "query": "What is the zero liability window for card disputes?",
        "should_access": ["card_dispute_policy.pdf"],
        "should_not_access": [],
    },
]


def run_regression() -> dict:
    """Run regression tests and return pass/fail results."""
    pipeline = RAGPipeline(llm=get_llm())
    results = {"tests": [], "passed": 0, "failed": 0, "total": 0}

    # Quality regression tests
    scores = {"context_precision": [], "context_recall": [], "faithfulness": [], "answer_relevancy": []}

    for case in EVAL_DATASET[:5]:
        rag_answer = pipeline.answer(case["question"])
        context_texts = [c.content for c in rag_answer.contexts]

        fp = judge_faithfulness(rag_answer.answer, context_texts)
        ar = judge_answer_relevancy(case["question"], rag_answer.answer)
        cp = judge_context_precision(case["question"], context_texts)
        cr = judge_context_recall(case["question"], case["ground_truth"], context_texts)

        scores["faithfulness"].append(fp.score)
        scores["answer_relevancy"].append(ar.score)
        scores["context_precision"].append(cp.score)
        scores["context_recall"].append(cr.score)

    for metric, values in scores.items():
        avg = sum(values) / len(values) if values else 0
        threshold = BASELINE_THRESHOLDS[metric]
        passed = avg >= threshold
        test = {
            "name": f"quality_{metric}",
            "type": "quality_regression",
            "score": round(avg, 3),
            "threshold": threshold,
            "passed": passed,
        }
        results["tests"].append(test)
        results["total"] += 1
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Role-based access regression tests
    for role_case in ROLE_TEST_CASES:
        rag_answer = pipeline.answer(role_case["query"], user_role=role_case["role"])
        retrieved_sources = [c.source for c in rag_answer.contexts]

        access_ok = all(
            any(expected in src for src in retrieved_sources)
            for expected in role_case["should_access"]
        ) if role_case["should_access"] else True

        restriction_ok = all(
            not any(forbidden in src for src in retrieved_sources)
            for forbidden in role_case["should_not_access"]
        )

        passed = access_ok and restriction_ok
        test = {
            "name": f"role_access_{role_case['role']}",
            "type": "role_based_access",
            "role": role_case["role"],
            "retrieved_sources": retrieved_sources,
            "access_verified": access_ok,
            "restriction_verified": restriction_ok,
            "passed": passed,
        }
        results["tests"].append(test)
        results["total"] += 1
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

    results["all_passed"] = results["failed"] == 0

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, f"regression_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    log_event(logger, "regression suite complete",
              total=results["total"], passed=results["passed"], failed=results["failed"])
    _print_results(results, out_path)
    return results


def _print_results(results: dict, out_path: str) -> None:
    print("\n=== Regression Test Results ===")
    for test in results["tests"]:
        status = "PASS" if test["passed"] else "FAIL"
        if "score" in test:
            print(f"  [{status}] {test['name']}: {test['score']:.3f} (threshold: {test['threshold']})")
        else:
            print(f"  [{status}] {test['name']}: access={test['access_verified']}, restriction={test['restriction_verified']}")
    print(f"\n  Total: {results['total']} | Passed: {results['passed']} | Failed: {results['failed']}")
    print(f"  Results: {out_path}\n")


if __name__ == "__main__":
    run_regression()
