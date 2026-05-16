from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import requests


API_URL = "http://127.0.0.1:8000"

BASE_DIR = Path(__file__).resolve().parents[2]
GOLDEN_SET_PATH = BASE_DIR / "app" / "eval" / "golden_set.json"
REPORTS_DIR = BASE_DIR / "reports"

RESULTS_CSV_PATH = REPORTS_DIR / "eval_results.csv"
SUMMARY_JSON_PATH = REPORTS_DIR / "eval_summary.json"


def load_golden_set() -> list[dict[str, Any]]:
    with GOLDEN_SET_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def call_api(question: str, architecture: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_URL}/ask",
        json={
            "question": question,
            "architecture": architecture,
            "session_id": "eval-session",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def extract_tool_names(trace: list[dict[str, Any]]) -> list[str]:
    tool_names = []

    for step in trace:
        step_name = step.get("name")
        if step_name:
            tool_names.append(step_name)

        output = step.get("output", {})
        if isinstance(output, dict) and output.get("tool_name"):
            tool_names.append(output["tool_name"])

    return tool_names


def extract_intent(trace: list[dict[str, Any]]) -> str | None:
    for step in trace:
        output = step.get("output", {})
        if isinstance(output, dict) and output.get("intent"):
            return output["intent"]
    return None


def contains_all(answer: str, expected_values: list[str]) -> bool:
    answer_lower = answer.lower()
    return all(str(value).lower() in answer_lower for value in expected_values)


def contains_forbidden(answer: str, forbidden_values: list[str]) -> bool:
    answer_lower = answer.lower()
    return any(str(value).lower() in answer_lower for value in forbidden_values)


def evaluate_case(case: dict[str, Any], architecture: str) -> dict[str, Any]:
    started = time.perf_counter()

    question = case["question"]

    try:
        result = call_api(question, architecture)
        error = ""

        answer = result.get("answer", "")
        trace = result.get("trace", [])
        tools = extract_tool_names(trace)
        intent = extract_intent(trace)

        expected_tool = case.get("expected_tool")
        expected_intent = case.get("expected_intent")

        if architecture == "baseline":
            # baseline не завжди має router intent, тому intent accuracy для нього не штрафуємо жорстко
            intent_ok = True
        else:
            intent_ok = intent == expected_intent

        if expected_tool == "none":
            tool_ok = len(trace) == 0 or "none" in tools or result.get("data", {}).get("scope") == "out_of_scope"
        else:
            tool_ok = expected_tool in tools

        must_include_ok = contains_all(answer, case.get("must_include", []))
        forbidden_ok = not contains_forbidden(answer, case.get("forbidden_phrases", []))

        success = intent_ok and tool_ok and must_include_ok and forbidden_ok

        latency_ms = result.get(
            "latency_ms",
            round((time.perf_counter() - started) * 1000, 2),
        )

        return {
            "case_id": case["id"],
            "architecture": architecture,
            "question": question,
            "status": "ok",
            "success": success,
            "intent_expected": expected_intent,
            "intent_actual": intent,
            "intent_ok": intent_ok,
            "tool_expected": expected_tool,
            "tools_actual": ", ".join(tools),
            "tool_ok": tool_ok,
            "must_include_ok": must_include_ok,
            "forbidden_ok": forbidden_ok,
            "latency_ms": latency_ms,
            "trace_steps": len(trace),
            "answer": answer,
            "error": error,
        }

    except Exception as error:
        return {
            "case_id": case["id"],
            "architecture": architecture,
            "question": question,
            "status": "error",
            "success": False,
            "intent_expected": case.get("expected_intent"),
            "intent_actual": "",
            "intent_ok": False,
            "tool_expected": case.get("expected_tool"),
            "tools_actual": "",
            "tool_ok": False,
            "must_include_ok": False,
            "forbidden_ok": False,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "trace_steps": 0,
            "answer": "",
            "error": str(error),
        }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    for architecture in ["baseline", "crew"]:
        rows = [row for row in results if row["architecture"] == architecture]

        if not rows:
            continue

        success_count = sum(1 for row in rows if row["success"])
        total_count = len(rows)

        latencies = sorted(float(row["latency_ms"]) for row in rows)
        p50_index = int(len(latencies) * 0.5)
        p95_index = min(int(len(latencies) * 0.95), len(latencies) - 1)

        tool_ok_count = sum(1 for row in rows if row["tool_ok"])
        grounded_ok_count = sum(1 for row in rows if row["must_include_ok"])

        summary[architecture] = {
            "total_cases": total_count,
            "success_count": success_count,
            "success_rate": round(success_count / total_count, 4),
            "tool_selection_accuracy": round(tool_ok_count / total_count, 4),
            "groundedness_proxy": round(grounded_ok_count / total_count, 4),
            "latency_p50_ms": round(latencies[p50_index], 2),
            "latency_p95_ms": round(latencies[p95_index], 2),
            "avg_trace_steps": round(
                sum(row["trace_steps"] for row in rows) / total_count,
                2,
            ),
            "cost_per_task_usd": 0,
            "tokens_per_task": 0,
        }

    if "baseline" in summary and "crew" in summary:
        baseline_steps = summary["baseline"]["avg_trace_steps"]
        crew_steps = summary["crew"]["avg_trace_steps"]

        summary["comparison"] = {
            "crew_extra_trace_steps": round(crew_steps - baseline_steps, 2),
            "note": (
                "Cost and token metrics are 0 because this stage uses deterministic "
                "local rule-based agents without LLM calls."
            ),
        }

    return summary


def save_results(results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    with RESULTS_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    with SUMMARY_JSON_PATH.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)


def main() -> None:
    golden_set = load_golden_set()
    results = []

    print("Running eval...")
    print(f"Golden set cases: {len(golden_set)}")

    for case in golden_set:
        for architecture in case["architectures"]:
            row = evaluate_case(case, architecture)
            results.append(row)

            status_icon = "✅" if row["success"] else "❌"
            print(
                f"{status_icon} {row['case_id']} | "
                f"{architecture} | "
                f"{row['latency_ms']} ms"
            )

    summary = summarize(results)
    save_results(results, summary)

    print("\nSummary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    print(f"\nSaved: {RESULTS_CSV_PATH}")
    print(f"Saved: {SUMMARY_JSON_PATH}")


if __name__ == "__main__":
    main()