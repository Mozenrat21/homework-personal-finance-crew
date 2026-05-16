from __future__ import annotations

import time
from typing import Any

from app.schemas import AskResponse, TraceStep
from app.tracing import traceable
from app.tools.finance_tools import (
    credit_card_behavior,
    dataset_summary,
    last_payment,
    late_night_delivery_stats,
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


def _trace_step(
    name: str,
    role: str,
    started: float,
    input_data: dict[str, Any],
    output_data: Any,
) -> TraceStep:
    return TraceStep(
        name=name,
        role=role,
        input=input_data,
        output=output_data,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )


@traceable(name="router_agent", run_type="chain")
def router_agent(question: str) -> tuple[dict[str, Any], TraceStep]:
    started = time.perf_counter()
    q = question.lower().strip()

    if _contains_any(q, ["акції", "stock", "stocks", "crypto", "крипт", "bitcoin", "інвестуй", "купи"]):
        intent = "out_of_scope"
    elif _contains_any(q, ["fraud", "шахрай", "підозр", "не робив", "не робила", "booking", "aliexpress"]):
        intent = "fraud_escalation"
    elif _contains_any(q, ["якщо", "вдвічі", "половин", "50%"]):
        intent = "simulation"
    elif _contains_any(q, ["зеконом", "економ", "$200", "200"]):
        intent = "savings_advice"
    elif _contains_any(q, ["останн", "last", "дата"]) and _contains_any(q, ["netflix"]):
        intent = "last_payment"
    elif _contains_any(q, ["підпис", "subscription", "netflix", "sportlife", "spotify"]):
        intent = "subscriptions"
    elif _contains_any(q, ["кав", "coffee"]):
        intent = "coffee"
    elif _contains_any(q, ["достав", "delivery", "glovo", "bolt food", "uber eats"]):
        intent = "delivery"
    elif _contains_any(q, ["вихідн", "weekend", "будні"]):
        intent = "weekend"
    elif _contains_any(q, ["кредит", "credit"]):
        intent = "credit_card"
    elif _contains_any(q, ["топ", "top", "категор"]):
        intent = "top_categories"
    else:
        intent = "dataset_summary"

    output = {
        "intent": intent,
        "question": question,
    }

    return output, _trace_step(
        name="router_agent",
        role="intent_classifier",
        started=started,
        input_data={"question": question},
        output_data=output,
    )

@traceable(name="data_analyst_agent", run_type="tool")
def data_analyst_agent(route: dict[str, Any]) -> tuple[dict[str, Any], TraceStep]:
    started = time.perf_counter()
    intent = route["intent"]

    if intent == "out_of_scope":
        tool_name = "none"
        data = {
            "scope": "out_of_scope",
            "message": "Investment trading requests are outside assistant scope.",
        }
    
    elif intent == "fraud_escalation":
        tool_name = "suspicious_transactions"
        data = suspicious_transactions()

    elif intent == "savings_advice":
        tool_name = "savings_opportunities"
        data = savings_opportunities(target_amount=200)

    elif intent == "last_payment":
        tool_name = "last_payment"
        data = last_payment("Netflix")

    elif intent == "subscriptions":
        tool_name = "subscriptions_summary"
        data = subscriptions_summary()

    elif intent == "coffee":
        tool_name = "monthly_category_spending"
        data = monthly_category_spending("coffee")

    elif intent == "delivery":
        tool_name = "late_night_delivery_stats"
        data = late_night_delivery_stats()

    elif intent == "weekend":
        tool_name = "weekend_vs_weekday_stats"
        data = weekend_vs_weekday_stats()

    elif intent == "credit_card":
        tool_name = "credit_card_behavior"
        data = credit_card_behavior()

    elif intent == "top_categories":
        tool_name = "top_categories"
        data = top_categories(limit=5)

    elif intent == "simulation":
        tool_name = "simulate_category_reduction"
        data = simulate_category_reduction(
            category="delivery",
            reduction_pct=0.5,
            months=12,
        )

    else:
        tool_name = "dataset_summary"
        data = dataset_summary()

    output = {
        "intent": intent,
        "tool_name": tool_name,
        "tool_result": data,
    }

    return output, _trace_step(
        name="data_analyst_agent",
        role="financial_data_tool_executor",
        started=started,
        input_data=route,
        output_data=output,
    )


@traceable(name="advisor_agent", run_type="chain")
def advisor_agent(analysis: dict[str, Any]) -> tuple[str, TraceStep]:
    started = time.perf_counter()
    intent = analysis["intent"]
    data = analysis["tool_result"]

    if intent == "out_of_scope":
        answer = (
            "Це поза моїм скоупом. Я не можу купувати акції, криптовалюту або давати "
            "інвестиційні накази. Можу допомогти з аналізом витрат, підписок, доставки, "
            "кави, кредитної картки та підозрілих транзакцій."
        )

    elif intent == "fraud_escalation":
        answer = (
            "Це схоже на потенційний fraud-сценарій. Я не можу самостійно блокувати картку "
            "або оформлювати chargeback. Рекомендую: 1) заблокувати картку в застосунку; "
            "2) звернутися до служби підтримки; 3) перевірити останні транзакції по credit card. "
            f"У даних знайдено {data['suspicious_transactions_count']} підозрілі транзакції."
        )

    elif intent == "savings_advice":
        items = data.get("opportunities", [])
        parts = [
            f"{item['area']}: приблизно ${item['estimated_monthly_saving']}/міс ({item['reason']})"
            for item in items
        ]

        answer = (
            f"Знайшов потенційну економію ${data['estimated_total_saving']}/міс. "
            f"Ціль $200 {'закривається' if data['target_reached'] else 'поки не закривається повністю'}. "
            f"Основні напрямки: {'; '.join(parts)}."
        )

    elif intent == "last_payment":
        if data["found"]:
            answer = (
                f"Останній платіж за {data['merchant']}: " 
                f"{data['last_payment_date']}, сума ${abs(data['amount'])}."
            )
        else:
            answer = "Не знайшов платіж за цим merchant."

    elif intent == "subscriptions":
        forgotten = data.get("possible_forgotten_subscriptions", [])
        if forgotten:
            answer = "Можливі забуті підписки: " + "; ".join(
                f"{item['merchant']} — ${item['avg_payment']}/міс, останній платіж {item['last_payment']}"
                for item in forgotten
            )
        else:
            answer = "Очевидно забутих підписок не знайшов."

    elif intent == "coffee":
        months = data["months"]
        last_month = months[-1] if months else None
        answer = (
            f"На каву за останній місяць: ${last_month['total_spent']} "
            f"за {last_month['transactions_count']} транзакцій. "
            "Це стабільна щомісячна звичка."
            if last_month
            else "Не знайшов витрат на каву."
        )

    elif intent == "delivery":
        answer = (
            f"Доставка: ${data['delivery_total_spent']} загалом. "
            f"Після 21:00 — ${data['late_night_total_spent']}, "
            f"це {data['late_night_share_pct']}% замовлень. "
            "Це хороший кандидат для економії без болючого урізання всього бюджету."
        )

    elif intent == "weekend":
        answer = (
            f"У будні середня транзакція ${data['weekday_avg_transaction']}, "
            f"у вихідні ${data['weekend_avg_transaction']}. "
            f"Weekend spike: {data['weekend_spike_pct']}%."
        )

    elif intent == "credit_card":
        answer = (
            f"По кредитній картці {data['credit_card_transactions_count']} транзакцій. "
            f"Місяців із платежем, схожим на minimum payment: {data['minimum_like_payment_months']}. "
            "Це ризик повільного погашення боргу."
        )

    elif intent == "top_categories":
        categories = data["categories"]
        answer = "Топ категорій витрат: " + "; ".join(
            f"{item['category']} — ${item['total_spent']}"
            for item in categories
        )

    elif intent == "simulation":
        answer = (
            f"Якщо зменшити витрати на {data['category']} на "
            f"{int(data['reduction_pct'] * 100)}%, економія за "
            f"{data['months']} міс. складе приблизно ${data['estimated_saving_total']}."
        )

    else:
        answer = (
            f"У датасеті {data['rows']} транзакції. "
            f"Період: {data['date_min']} — {data['date_max']}. "
            "Можу аналізувати витрати, доставку, каву, підписки, кредитну картку та suspicious транзакції."
        )

    return answer, _trace_step(
        name="advisor_agent",
        role="answer_synthesizer",
        started=started,
        input_data={"intent": intent, "tool_result": data},
        output_data={"answer": answer},
    )


@traceable(name="run_crew", run_type="chain")
def run_crew(question: str, session_id: str | None = None) -> AskResponse:
    trace: list[TraceStep] = []

    route, route_step = router_agent(question)
    trace.append(route_step)

    analysis, analysis_step = data_analyst_agent(route)
    trace.append(analysis_step)

    answer, answer_step = advisor_agent(analysis)
    trace.append(answer_step)

    return AskResponse(
        architecture="crew",
        answer=answer,
        data=analysis["tool_result"],
        trace=trace,
        cost_usd=0,
        tokens=0,
    )