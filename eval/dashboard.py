"""Evaluation reporting dashboard.

Generates HTML dashboard from evaluation results. Aggregates metrics
across runs and visualizes trends, per-category breakdowns, and
regression test history.

Usage: python -m eval.dashboard
"""
import glob
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

from app.logging_utils import get_logger, log_event

logger = get_logger("eval.dashboard")

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
DASHBOARD_PATH = os.path.join(RESULTS_DIR, "dashboard.html")


def _load_eval_results() -> list[dict]:
    pattern = os.path.join(RESULTS_DIR, "eval_*.json")
    results = []
    for filepath in sorted(glob.glob(pattern)):
        with open(filepath, "r") as f:
            data = json.load(f)
            data["_filename"] = os.path.basename(filepath)
            results.append(data)
    return results


def _load_regression_results() -> list[dict]:
    pattern = os.path.join(RESULTS_DIR, "regression_*.json")
    results = []
    for filepath in sorted(glob.glob(pattern)):
        with open(filepath, "r") as f:
            data = json.load(f)
            data["_filename"] = os.path.basename(filepath)
            results.append(data)
    return results


def _load_drift_results() -> list[dict]:
    pattern = os.path.join(RESULTS_DIR, "drift_*.json")
    results = []
    for filepath in sorted(glob.glob(pattern)):
        with open(filepath, "r") as f:
            data = json.load(f)
            data["_filename"] = os.path.basename(filepath)
            results.append(data)
    return results


def generate_dashboard() -> str:
    """Generate an HTML dashboard from all evaluation results."""
    eval_results = _load_eval_results()
    regression_results = _load_regression_results()
    drift_results = _load_drift_results()

    metrics_over_time = []
    for result in eval_results:
        if "summary" in result:
            metrics_over_time.append({
                "run": result["_filename"],
                **result["summary"],
            })

    category_breakdown = {}
    if eval_results:
        latest = eval_results[-1]
        for item in latest.get("items", []):
            cat = item.get("category", "unknown")
            if cat not in category_breakdown:
                category_breakdown[cat] = {"count": 0, "avg_overall": 0, "scores": []}
            category_breakdown[cat]["count"] += 1
            if "end_to_end" in item:
                category_breakdown[cat]["scores"].append(item["end_to_end"]["overall"])

    for cat in category_breakdown:
        scores = category_breakdown[cat]["scores"]
        category_breakdown[cat]["avg_overall"] = round(sum(scores) / len(scores), 3) if scores else 0

    html = _render_html(metrics_over_time, category_breakdown, regression_results, drift_results)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    log_event(logger, "dashboard generated", path=DASHBOARD_PATH, eval_runs=len(eval_results))
    print(f"\nDashboard generated: {DASHBOARD_PATH}\n")
    return DASHBOARD_PATH


def _render_html(metrics: list, categories: dict, regressions: list, drifts: list) -> str:
    metrics_rows = ""
    for m in metrics:
        metrics_rows += f"""<tr>
            <td>{m['run']}</td>
            <td>{m.get('context_precision', 'N/A')}</td>
            <td>{m.get('context_recall', 'N/A')}</td>
            <td>{m.get('faithfulness', 'N/A')}</td>
            <td>{m.get('answer_relevancy', 'N/A')}</td>
            <td>{m.get('end_to_end_overall', 'N/A')}</td>
        </tr>"""

    category_rows = ""
    for cat, data in categories.items():
        category_rows += f"""<tr>
            <td>{cat}</td>
            <td>{data['count']}</td>
            <td>{data['avg_overall']}</td>
        </tr>"""

    regression_rows = ""
    for reg in regressions[-5:]:
        status = "PASS" if reg.get("all_passed") else "FAIL"
        color = "#28a745" if reg.get("all_passed") else "#dc3545"
        regression_rows += f"""<tr>
            <td>{reg['_filename']}</td>
            <td style="color:{color};font-weight:bold">{status}</td>
            <td>{reg.get('passed', 0)}/{reg.get('total', 0)}</td>
        </tr>"""

    drift_rows = ""
    for d in drifts[-5:]:
        emb = d.get("embedding_drift", {})
        pmt = d.get("prompt_drift", {})
        emb_status = "DRIFT" if emb.get("drift_detected") else "OK"
        pmt_status = "DRIFT" if pmt.get("drift_detected") else "OK"
        drift_rows += f"""<tr>
            <td>{d['_filename']}</td>
            <td>{emb_status} ({emb.get('avg_similarity', 'N/A')})</td>
            <td>{pmt_status} ({pmt.get('avg_relevancy', 'N/A')})</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>FinBot RAG Evaluation Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; background: #f5f5f5; }}
        h1 {{ color: #1a237e; }}
        h2 {{ color: #283593; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #e8eaf6; font-weight: 600; }}
        tr:hover {{ background: #f5f5f5; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; margin: 15px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #1a237e; }}
        .metric-label {{ font-size: 0.85em; color: #666; }}
        .timestamp {{ color: #999; font-size: 0.85em; }}
    </style>
</head>
<body>
    <h1>FinBot RAG Evaluation Dashboard</h1>
    <p class="timestamp">Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</p>

    <div class="card">
        <h2>Quality Metrics Over Time</h2>
        <table>
            <tr><th>Run</th><th>Context Precision</th><th>Context Recall</th><th>Faithfulness</th><th>Answer Relevancy</th><th>E2E Overall</th></tr>
            {metrics_rows or '<tr><td colspan="6">No evaluation runs found</td></tr>'}
        </table>
    </div>

    <div class="card">
        <h2>Category Breakdown (Latest Run)</h2>
        <table>
            <tr><th>Category</th><th>Questions</th><th>Avg Overall Score</th></tr>
            {category_rows or '<tr><td colspan="3">No data available</td></tr>'}
        </table>
    </div>

    <div class="card">
        <h2>Regression Test History</h2>
        <table>
            <tr><th>Run</th><th>Status</th><th>Tests Passed</th></tr>
            {regression_rows or '<tr><td colspan="3">No regression runs found</td></tr>'}
        </table>
    </div>

    <div class="card">
        <h2>Drift Detection History</h2>
        <table>
            <tr><th>Run</th><th>Embedding Drift</th><th>Prompt Drift</th></tr>
            {drift_rows or '<tr><td colspan="3">No drift detection runs found</td></tr>'}
        </table>
    </div>
</body>
</html>"""


if __name__ == "__main__":
    generate_dashboard()
