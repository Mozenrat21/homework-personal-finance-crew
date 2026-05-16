from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"
BASE_DIR = Path(__file__).resolve().parent
GOLDEN_SET_PATH = BASE_DIR / "app" / "eval" / "golden_set.json"


st.set_page_config(
    page_title="Personal Finance Crew",
    page_icon="💸",
    layout="wide",
)


def call_ask_api(
    question: str,
    architecture: str,
    session_id: str = "streamlit-demo",
) -> dict[str, Any]:
    """
    Викликає FastAPI endpoint /ask.
    """
    response = requests.post(
        f"{API_URL}/ask",
        json={
            "question": question,
            "architecture": architecture,
            "session_id": session_id,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def call_health() -> bool:
    """
    Перевіряє, чи запущений FastAPI backend.
    """
    try:
        response = requests.get(f"{API_URL}/health", timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False


def load_golden_set() -> list[dict[str, Any]]:
    with GOLDEN_SET_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def extract_tool_names(trace: list[dict[str, Any]]) -> list[str]:
    tool_names: list[str] = []

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


def evaluate_case_for_ui(
    case: dict[str, Any],
    architecture: str,
    run_id: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    question = case["question"]

    try:
        result = call_ask_api(
            question=question,
            architecture=architecture,
            session_id=f"streamlit-eval-{run_id}-{case['id']}-{architecture}",
        )

        answer = result.get("answer", "")
        trace = result.get("trace", [])
        tools = extract_tool_names(trace)
        intent = extract_intent(trace)

        expected_tool = case.get("expected_tool")
        expected_intent = case.get("expected_intent")

        if architecture == "baseline":
            intent_ok = True
        else:
            intent_ok = intent == expected_intent

        if expected_tool == "none":
            tool_ok = (
                len(trace) == 0
                or "none" in tools
                or result.get("data", {}).get("scope") == "out_of_scope"
            )
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
            "tokens": int(result.get("tokens", 0) or 0),
            "cost_usd": float(result.get("cost_usd", 0) or 0),
            "warnings": " | ".join(result.get("warnings", [])),
            "question": question,
            "answer": answer,
            "error": "",
        }

    except Exception as error:
        return {
            "case_id": case["id"],
            "architecture": architecture,
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
            "tokens": 0,
            "cost_usd": 0.0,
            "warnings": "",
            "question": question,
            "answer": "",
            "error": str(error),
        }


def summarize_eval(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary_rows: list[dict[str, Any]] = []

    for architecture in ["baseline", "crew"]:
        arch_rows = [row for row in rows if row["architecture"] == architecture]

        if not arch_rows:
            continue

        total_count = len(arch_rows)
        success_count = sum(1 for row in arch_rows if row["success"])
        tool_ok_count = sum(1 for row in arch_rows if row["tool_ok"])
        grounded_ok_count = sum(1 for row in arch_rows if row["must_include_ok"])

        latencies = sorted(float(row["latency_ms"]) for row in arch_rows)
        p50_index = int(len(latencies) * 0.5)
        p95_index = min(int(len(latencies) * 0.95), len(latencies) - 1)

        total_tokens = sum(int(row.get("tokens", 0) or 0) for row in arch_rows)
        total_cost = sum(float(row.get("cost_usd", 0) or 0) for row in arch_rows)
        avg_trace_steps = sum(int(row["trace_steps"]) for row in arch_rows) / total_count

        summary_rows.append(
            {
                "architecture": architecture,
                "total_cases": total_count,
                "success_count": success_count,
                "success_rate": round(success_count / total_count, 4),
                "tool_selection_accuracy": round(tool_ok_count / total_count, 4),
                "groundedness_proxy": round(grounded_ok_count / total_count, 4),
                "latency_p50_ms": round(latencies[p50_index], 2),
                "latency_p95_ms": round(latencies[p95_index], 2),
                "avg_trace_steps": round(avg_trace_steps, 2),
                "tokens_per_task": round(total_tokens / total_count, 2),
                "cost_per_task_usd": round(total_cost / total_count, 8),
            }
        )

    return summary_rows


def run_full_golden_eval() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    golden_set = load_golden_set()
    rows: list[dict[str, Any]] = []
    run_id = str(int(time.time()))

    progress_total = sum(len(case["architectures"]) for case in golden_set)
    progress = st.progress(0)
    counter = 0

    for case in golden_set:
        for architecture in case["architectures"]:
            row = evaluate_case_for_ui(
                case=case,
                architecture=architecture,
                run_id=run_id,
            )
            rows.append(row)

            counter += 1
            progress.progress(counter / progress_total)

    summary_rows = summarize_eval(rows)
    return rows, summary_rows


def render_trace(trace: list[dict[str, Any]]) -> None:
    """
    Виводить trace агентів та tools у зручному вигляді.
    """
    if not trace:
        st.info("Trace порожній.")
        return

    for index, step in enumerate(trace, start=1):
        with st.expander(
            f"{index}. {step.get('name')} · {step.get('role')} · {step.get('latency_ms')} ms",
            expanded=False,
        ):
            st.markdown("**Input**")
            st.json(step.get("input", {}))

            st.markdown("**Output**")
            st.json(step.get("output", {}))


def render_response(result: dict[str, Any]) -> None:
    """
    Виводить відповідь агента, метрики й trace.
    """
    st.subheader("Відповідь")
    st.success(result["answer"])

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Architecture", result["architecture"])
    col2.metric("Latency, ms", result.get("latency_ms", 0))
    col3.metric("Cost, $", result.get("cost_usd", 0))
    col4.metric("Tokens", result.get("tokens", 0))

    warnings = result.get("warnings", [])
    if warnings:
        st.warning(" | ".join(warnings))

    with st.expander("Дані з tools", expanded=False):
        st.json(result.get("data", {}))

    st.subheader("Trace")
    render_trace(result.get("trace", []))


st.title("💸 Personal Finance Crew")
st.caption("Lesson 11 · Multi-Agent Orchestration · Personal Finance Coach")

with st.sidebar:
    st.header("Налаштування")

    architecture = st.radio(
        "Архітектура",
        options=["baseline", "crew"],
        index=1,
        help="baseline = один агент; crew = router + analyst + advisor",
    )

    st.divider()

    is_backend_alive = call_health()

    if is_backend_alive:
        st.success("FastAPI backend працює")
    else:
        st.error("FastAPI backend не відповідає")
        st.code("python -m uvicorn app.main:app --reload", language="powershell")

    st.divider()

    st.markdown(
        """
        **Що перевіряємо по ДЗ:**

        - baseline vs crew;
        - trace агентів;
        - latency;
        - tokens;
        - cost;
        - grounded answers;
        - fraud escalation;
        - full golden set eval.
        """
    )


tab_ask, tab_eval = st.tabs(["Ask", "Eval"])

with tab_ask:
    st.subheader("Запит до фінансового помічника")

    example_questions = [
        "Скільки я витрачаю на каву?",
        "А за останній місяць?",
        "Де можна зекономити $200 цього місяця?",
        "Дата останнього платежу за Netflix?",
        "Я не робив транзакцію Booking.com, це шахрайство?",
        "Порівняй витрати у будні та вихідні",
        "Якщо зменшити витрати на доставку вдвічі — яка економія за рік?",
        "Топ-5 категорій витрат",
    ]

    selected_example = st.selectbox(
        "Приклад запиту",
        options=[""] + example_questions,
    )

    default_question = selected_example or "Скільки я витрачаю на каву?"

    question = st.text_area(
        "Твій запит",
        value=default_question,
        height=100,
    )

    submit = st.button("Submit", type="primary")

    if submit:
        if not question.strip():
            st.warning("Введи запит.")
        elif not is_backend_alive:
            st.error("Спочатку запусти FastAPI backend.")
            st.code("python -m uvicorn app.main:app --reload", language="powershell")
        else:
            with st.spinner("Агент думає. Не довго, він не в черзі до банкомату..."):
                try:
                    result = call_ask_api(question, architecture)
                    render_response(result)
                except requests.HTTPError as error:
                    st.error(f"API повернув помилку: {error}")
                except requests.RequestException as error:
                    st.error(f"Не вдалося підключитися до API: {error}")


with tab_eval:
    st.subheader("Full Golden Set Eval")

    st.info(
        "Цей запуск проходить повний golden set із app/eval/golden_set.json "
        "для baseline і crew. Потрібен запущений FastAPI backend."
    )

    if st.button("Run full golden set eval", type="primary"):
        if not is_backend_alive:
            st.error("Спочатку запусти FastAPI backend.")
            st.code("python -m uvicorn app.main:app --reload", language="powershell")
        else:
            with st.spinner("Запускаю повний golden set. Так, це довше за smoke eval, але вже по-дорослому..."):
                rows, summary_rows = run_full_golden_eval()

            st.subheader("Summary")
            st.dataframe(summary_rows, use_container_width=True)

            st.subheader("Detailed results")
            st.dataframe(rows, use_container_width=True)

            failed_rows = [row for row in rows if not row["success"]]

            if failed_rows:
                st.error(f"Є failed cases: {len(failed_rows)}")
                st.dataframe(failed_rows, use_container_width=True)
            else:
                st.success("Усі golden set cases пройдено успішно.")

            with st.expander("Raw JSON", expanded=False):
                st.code(
                    json.dumps(
                        {
                            "summary": summary_rows,
                            "results": rows,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    language="json",
                )