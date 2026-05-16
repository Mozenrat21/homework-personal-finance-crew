from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from app.tracing import traceable


load_dotenv(override=True)


CRITICAL_TERMS = {
    "delivery": ["delivery", "доставка", "доставку", "доставки"],
    "coffee": ["coffee", "кава", "каву", "кави"],
    "subscriptions": ["subscriptions", "підписки", "підписок", "підписка"],
    "credit_card": ["credit", "credit card", "кредит", "кредитна", "кредитній", "кредитної", "картка", "картці"],
    "weekday_exact": ["будні"],
    "weekend_exact": ["вихідні"],
    "Sportlife": ["Sportlife", "sportlife"],
    "Netflix": ["Netflix", "netflix"],
    "Booking.com": ["Booking.com", "booking.com"],
    "AliExpress": ["AliExpress", "aliexpress"],
    "groceries": ["groceries", "продукти"],
}


def is_llm_enabled() -> bool:
    """
    LLM вмикається тільки через USE_LLM=true і наявний OPENROUTER_API_KEY.
    """
    return (
        os.getenv("USE_LLM", "false").lower() == "true"
        and bool(os.getenv("OPENROUTER_API_KEY"))
    )


def _extract_numbers(text: str) -> list[str]:
    """
    Витягує числа з fallback answer.
    Потрібно, щоб LLM не загубив важливі суми.
    """
    return re.findall(r"\d+(?:\.\d+)?", text)

def _calculate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    """
    Оцінює вартість LLM-виклику на основі token usage.

    Ціни беруться з .env:
    - OPENROUTER_INPUT_PRICE_PER_1M
    - OPENROUTER_OUTPUT_PRICE_PER_1M
    """
    input_price_per_1m = float(os.getenv("OPENROUTER_INPUT_PRICE_PER_1M", "0"))
    output_price_per_1m = float(os.getenv("OPENROUTER_OUTPUT_PRICE_PER_1M", "0"))

    input_cost = (prompt_tokens / 1_000_000) * input_price_per_1m
    output_cost = (completion_tokens / 1_000_000) * output_price_per_1m

    return round(input_cost + output_cost, 8)


def _missing_required_parts(fallback_answer: str, llm_answer: str) -> list[str]:
    """
    Перевіряє, чи LLM не загубив важливі числа або ключові сутності.

    Логіка:
    - числа мають залишитися точно такими самими;
    - category labels можуть бути або англійською, або українською;
    - merchant names мають залишитися впізнаваними.
    """
    missing: list[str] = []

    fallback_lower = fallback_answer.lower()
    llm_lower = llm_answer.lower()

    for number in _extract_numbers(fallback_answer):
        if number not in llm_answer:
            missing.append(number)

    for canonical_term, allowed_variants in CRITICAL_TERMS.items():
        term_is_required = any(
            variant.lower() in fallback_lower
            for variant in allowed_variants
        )

        if not term_is_required:
            continue

        term_is_present = any(
            variant.lower() in llm_lower
            for variant in allowed_variants
        )

        if not term_is_present:
            missing.append(canonical_term)

    if "$" in fallback_answer:
        has_usd_marker = "$" in llm_answer or "usd" in llm_lower
        has_uah_marker = "грн" in llm_lower or "uah" in llm_lower

        if not has_usd_marker:
            missing.append("USD currency marker")

        if has_uah_marker:
            missing.append("currency changed to UAH")


    return missing


@traceable(name="openrouter_answer_synthesizer", run_type="llm")
def generate_finance_answer(
    question: str,
    architecture: str,
    intent: str,
    tool_name: str,
    tool_result: dict[str, Any],
    fallback_answer: str,
) -> dict[str, Any]:
    """
    Генерує фінальну відповідь через OpenRouter LLM.

    Важливо:
    - LLM не рахує суми самостійно;
    - LLM формулює відповідь тільки на основі tool_result;
    - якщо LLM загубив важливі числа/слова — повертаємо fallback.
    """
    if not is_llm_enabled():
        return {
            "answer": fallback_answer,
            "tokens": 0,
            "cost_usd": 0,
            "used_llm": False,
            "warning": "LLM disabled. Used deterministic fallback answer.",
        }

    client = OpenAI(
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        timeout=8.0,
        default_headers={
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
            "X-OpenRouter-Title": os.getenv(
                "OPENROUTER_APP_NAME",
                "lesson-11-personal-finance-crew",
            ),
        },
    )

    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku")

    tool_result_json = json.dumps(
        tool_result,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a safe Personal Finance Coach. "
                "Use only provided tool results. Never invent numbers. "
                "Do not provide investment orders. "
                "Fraud or suspicious transactions must be escalated to support."
            ),
        },
        {
            "role": "user",
            "content": f"""
Відповідай українською, дружньо, на "ти", без менторства.

Правила:
- використовуй тільки числа з TOOL_RESULT;
- валюта датасету USD; суми показуй як $ або USD;
- ніколи не замінюй $ на грн або UAH;
- не вигадуй додаткові факти;
- не змінюй merchant names;
- збережи важливі суми, дати й категорії;
- якщо у fallback є технічні категорії delivery, coffee, subscriptions — збережи їх у дужках поряд з українським поясненням;
- якщо у fallback є слова будні та вихідні — збережи саме слова будні та вихідні;
- відповідь має бути коротка й actionable;
- не додавай зайвих фінальних питань;
- не використовуй фрази типу "Які думки?";
- пиши грамотно, без розмовних склейок слів;
- fraud/suspicious transactions тільки ескалюй до підтримки;
- out-of-scope запити відхиляй ввічливо.

Architecture: {architecture}
Intent: {intent}
Tool: {tool_name}

User question:
{question}

TOOL_RESULT:
{tool_result_json}

DETERMINISTIC_FALLBACK_ANSWER:
{fallback_answer}

Сформуй фінальну відповідь для користувача.
""",
        },
    ]

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=300,
        )

        llm_answer = completion.choices[0].message.content.strip()

        usage = completion.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) if usage else 0
        cost_usd = _calculate_cost_usd(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        missing_parts = _missing_required_parts(
            fallback_answer=fallback_answer,
            llm_answer=llm_answer,
        )

        if missing_parts:
            return {
                "answer": fallback_answer,
                "tokens": total_tokens,
                "cost_usd": cost_usd,
                "used_llm": False,
                "warning": (
                    "LLM answer rejected because it missed required parts: "
                    + ", ".join(missing_parts)
                ),
            }

        return {
            "answer": llm_answer,
            "tokens": total_tokens,
            "cost_usd": cost_usd,
            "used_llm": True,
            "warning": "",
        }

    except Exception as error:
        return {
            "answer": fallback_answer,
            "tokens": 0,
            "cost_usd": 0,
            "used_llm": False,
            "warning": f"LLM failed, used fallback. Error: {error}",
        }