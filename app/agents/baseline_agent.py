from __future__ import annotations

import time
from typing import Any

from app.schemas import AskResponse, TraceStep
from app.tracing import traceable
from app.llm import generate_finance_answer
from app.tools.finance_tools import (
    credit_card_behavior,
    dataset_summary,
    late_night_delivery_stats,
    last_payment,
    monthly_category_spending,
    savings_opportunities,
    simulate_category_reduction,
    subscriptions_summary,
    suspicious_transactions,
    top_categories,
    weekend_vs_weekday_stats,
)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)

@traceable(name="baseline_run_tool", run_type="tool")
def _run_tool(name: str, role: str, tool_func, tool_input: dict[str, Any]) -> tuple[Any, TraceStep]:
    started = time.perf_counter()
    output = tool_func(**tool_input)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    return output, TraceStep(
        name=name,
        role=role,
        input=tool_input,
        output=output,
        latency_ms=latency_ms,
    )


@traceable(name="run_baseline", run_type="chain")
def run_baseline(question: str, session_id: str | None = None) -> AskResponse:
    """
    Single-agent baseline:
    один агент сам вибирає tool і сам формує відповідь.
    Поки без LLM — rule-based skeleton для перевірки API.
    """
    q = question.lower().strip()
    trace: list[TraceStep] = []

    if _contains_any(q, ["акції", "stock", "stocks", "crypto", "крипт", "bitcoin", "інвестуй", "купи"]):
        return AskResponse(
            architecture="baseline",
            answer=(
                "Це поза моїм скоупом. Я не можу купувати акції, криптовалюту або давати "
                "інвестиційні накази. Можу допомогти з аналізом витрат, підписок, доставки, "
                "кави, кредитної картки та підозрілих транзакцій."
            ),
            data={"scope": "out_of_scope"},
            trace=[],
            cost_usd=0,
            tokens=0,
        )

    if _contains_any(q, ["fraud", "шахрай", "підозр", "не робив", "не робила", "booking", "aliexpress"]):
        data, step = _run_tool(
            name="suspicious_transactions",
            role="single_agent_baseline",
            tool_func=suspicious_transactions,
            tool_input={},
        )
        trace.append(step)

        answer = (
            "Схоже на потенційно підозрілу операцію. Я не можу самостійно блокувати картку "
            "або оформлювати chargeback — це має зробити служба підтримки. "
            "Рекомендую заблокувати картку в застосунку та звернутися в підтримку. "
            f"У даних знайдено {data['suspicious_transactions_count']} підозрілі транзакції."
        )

    elif _contains_any(q, ["якщо", "вдвічі", "половин", "50%"]):
        data, step = _run_tool(
            name="simulate_category_reduction",
            role="single_agent_baseline",
            tool_func=simulate_category_reduction,
            tool_input={"category": "delivery", "reduction_pct": 0.5, "months": 12},
        )
        trace.append(step)

        answer = (
            f"Якщо зменшити витрати на доставку на 50%, "
            f"орієнтовна економія за рік: ${data['estimated_saving_total']}."
        )

    elif _contains_any(q, ["зеконом", "економ", "$200", "200"]):
        data, step = _run_tool(
            name="savings_opportunities",
            role="single_agent_baseline",
            tool_func=savings_opportunities,
            tool_input={"target_amount": 200},
        )
        trace.append(step)

        opportunity_text = "; ".join(
            f"{item['area']}: ${item['estimated_monthly_saving']}/міс ({item['reason']})"
            for item in data.get("opportunities", [])
        )

        answer = (
            f"Оцінив можливості економії на основі транзакцій. "
            f"Потенційна економія: ${data['estimated_total_saving']} на місяць. "
            f"Ціль $200 {'досягнута' if data['target_reached'] else 'поки не досягнута'}. "
            f"Основні напрямки: {opportunity_text}."
        )

    elif _contains_any(q, ["останн", "last", "дата"]) and _contains_any(q, ["netflix"]):
        data, step = _run_tool(
            name="last_payment",
            role="single_agent_baseline",
            tool_func=last_payment,
            tool_input={"merchant": "Netflix"},
        )
        trace.append(step)

        if data["found"]:
            answer = (
                f"Останній платіж за {data['merchant']}: "
                f"{data['last_payment_date']}, сума ${abs(data['amount'])}."
            )
        else:
            answer = "Не знайшов платіж за Netflix."

    elif _contains_any(q, ["підпис", "subscription", "netflix", "sportlife", "spotify"]):
        data, step = _run_tool(
            name="subscriptions_summary",
            role="single_agent_baseline",
            tool_func=subscriptions_summary,
            tool_input={},
        )
        trace.append(step)

        forgotten = data.get("possible_forgotten_subscriptions", [])
        if forgotten:
            forgotten_text = ", ".join(
                f"{item['merchant']} (${item['avg_payment']}/міс)"
                for item in forgotten
            )
            answer = f"Знайшов можливі забуті підписки: {forgotten_text}."
        else:
            answer = "Я не знайшов очевидно забутих підписок."

    elif _contains_any(q, ["кав", "coffee"]):
        data, step = _run_tool(
            name="monthly_category_spending",
            role="single_agent_baseline",
            tool_func=monthly_category_spending,
            tool_input={"category": "coffee"},
        )
        trace.append(step)

        months = data["months"]
        last_month = months[-1] if months else None
        answer = (
            f"Витрати на каву стабільно рахуються по місяцях. "
            f"Останній місяць: ${last_month['total_spent']} за "
            f"{last_month['transactions_count']} транзакцій."
            if last_month
            else "Не знайшов витрат на каву."
        )

    elif _contains_any(q, ["достав", "delivery", "glovo", "bolt food", "uber eats"]):
        data, step = _run_tool(
            name="late_night_delivery_stats",
            role="single_agent_baseline",
            tool_func=late_night_delivery_stats,
            tool_input={},
        )
        trace.append(step)

        answer = (
            f"На доставку витрачено ${data['delivery_total_spent']}. "
            f"Після 21:00 — ${data['late_night_total_spent']}, "
            f"це {data['late_night_share_pct']}% замовлень."
        )

    elif _contains_any(q, ["вихідн", "weekend", "будні"]):
        data, step = _run_tool(
            name="weekend_vs_weekday_stats",
            role="single_agent_baseline",
            tool_func=weekend_vs_weekday_stats,
            tool_input={},
        )
        trace.append(step)

        answer = (
            f"Середня транзакція у будні: ${data['weekday_avg_transaction']}, "
            f"у вихідні: ${data['weekend_avg_transaction']}. "
            f"Різниця: {data['weekend_spike_pct']}%."
        )

    elif _contains_any(q, ["кредит", "credit"]):
        data, step = _run_tool(
            name="credit_card_behavior",
            role="single_agent_baseline",
            tool_func=credit_card_behavior,
            tool_input={},
        )
        trace.append(step)

        answer = (
            f"По кредитній картці знайдено {data['credit_card_transactions_count']} транзакцій. "
            f"Місяців зі схожим на minimum payment платежем: {data['minimum_like_payment_months']}."
        )

    elif _contains_any(q, ["топ", "top", "категор"]):
        data, step = _run_tool(
            name="top_categories",
            role="single_agent_baseline",
            tool_func=top_categories,
            tool_input={"limit": 5},
        )
        trace.append(step)

        top = data["categories"][0]
        answer = (
            f"Топ категорія витрат: {top['category']} — "
            f"${top['total_spent']} за {top['transactions_count']} транзакцій."
        )

    else:
        data, step = _run_tool(
            name="dataset_summary",
            role="single_agent_baseline",
            tool_func=dataset_summary,
            tool_input={},
        )
        trace.append(step)

        answer = (
            "Я можу аналізувати витрати, підписки, доставку, каву, кредитну картку "
            "та підозрілі транзакції. "
            f"У датасеті {data['rows']} транзакції за період {data['date_min']} — {data['date_max']}."
        )

    tool_name = trace[-1].name if trace else "none"

    llm_result = generate_finance_answer(
        question=question,
        architecture="baseline",
        intent="single_agent_rule_based",
        tool_name=tool_name,
        tool_result=data,
        fallback_answer=answer,
    )

    final_answer = llm_result["answer"]
    warnings = []

    if llm_result.get("warning"):
        warnings.append(llm_result["warning"])

    return AskResponse(
        architecture="baseline",
        answer=final_answer,
        data=data,
        trace=trace,
        cost_usd=llm_result.get("cost_usd", 0),
        tokens=llm_result.get("tokens", 0),
        warnings=warnings,
    )