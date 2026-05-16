from __future__ import annotations

import json
import time
from typing import Any

import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="Personal Finance Crew",
    page_icon="💸",
    layout="wide",
)


def call_ask_api(question: str, architecture: str) -> dict[str, Any]:
    """
    Викликає FastAPI endpoint /ask.
    """
    response = requests.post(
        f"{API_URL}/ask",
        json={
            "question": question,
            "architecture": architecture,
            "session_id": "streamlit-demo",
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

    with st.expander("Дані з tools", expanded=False):
        st.json(result.get("data", {}))

    st.subheader("Trace")
    render_trace(result.get("trace", []))


def run_smoke_eval() -> list[dict[str, Any]]:
    """
    Міні-перевірка для UI.
    Повноцінний golden set зробимо окремим кроком у app/eval/golden_set.json.
    """
    questions = [
        "Скільки я витрачаю на каву?",
        "Де можна зекономити $200 цього місяця?",
        "Дата останнього платежу за Netflix?",
        "Я не робив транзакцію Booking.com, це шахрайство?",
        "Порівняй витрати у будні та вихідні",
    ]

    rows = []

    for question in questions:
        for architecture in ["baseline", "crew"]:
            started = time.perf_counter()

            try:
                result = call_ask_api(question, architecture)
                status = "ok"
                answer = result["answer"]
                latency_ms = result.get("latency_ms", 0)
                trace_steps = len(result.get("trace", []))
            except Exception as error:
                status = "error"
                answer = str(error)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                trace_steps = 0

            rows.append(
                {
                    "question": question,
                    "architecture": architecture,
                    "status": status,
                    "latency_ms": latency_ms,
                    "trace_steps": trace_steps,
                    "answer": answer,
                }
            )

    return rows


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
        - grounded answers;
        - fraud escalation.
        """
    )


tab_ask, tab_eval = st.tabs(["Ask", "Eval"])

with tab_ask:
    st.subheader("Запит до фінансового помічника")

    example_questions = [
        "Скільки я витрачаю на каву?",
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
    st.subheader("Smoke Eval")

    st.info(
        "Це поки швидка UI-перевірка. Повноцінний golden set на 15+ задач "
        "зробимо наступним кроком у файлі app/eval/golden_set.json."
    )

    if st.button("Run smoke eval"):
        if not is_backend_alive:
            st.error("Спочатку запусти FastAPI backend.")
        else:
            with st.spinner("Запускаю baseline vs crew..."):
                rows = run_smoke_eval()
                st.dataframe(rows, use_container_width=True)

                with st.expander("Raw JSON", expanded=False):
                    st.code(
                        json.dumps(rows, ensure_ascii=False, indent=2),
                        language="json",
                    )