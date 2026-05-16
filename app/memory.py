from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.schemas import AskResponse


@dataclass
class SessionMemory:
    last_question: str = ""
    last_effective_question: str = ""
    last_intent: str = ""
    last_category: str = ""
    last_merchant: str = ""


_SESSION_MEMORY: dict[str, SessionMemory] = {}


CATEGORY_KEYWORDS = {
    "coffee": ["кав", "coffee"],
    "delivery": ["достав", "delivery", "glovo", "bolt food", "uber eats"],
    "subscriptions": ["підпис", "subscription", "netflix", "sportlife", "spotify"],
    "credit_card": ["кредит", "credit", "картк"],
    "weekend": ["будні", "вихідні", "weekend"],
    "top_categories": ["топ", "top", "категор"],
}


MERCHANT_KEYWORDS = {
    "Netflix": ["netflix"],
    "Sportlife": ["sportlife"],
    "Booking.com": ["booking"],
    "AliExpress": ["aliexpress"],
}


FOLLOW_UP_PREFIXES = [
    "а ",
    "а за",
    "а якщо",
    "а минул",
    "а остан",
]

FOLLOW_UP_KEYWORDS = [
    "минул",
    "останн",
    "цей місяць",
    "за місяць",
    "за рік",
    "детальніше",
    "ще",
]


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _infer_category(question: str) -> str:
    q = question.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if _contains_any(q, keywords):
            return category

    return ""


def _infer_merchant(question: str) -> str:
    q = question.lower()

    for merchant, keywords in MERCHANT_KEYWORDS.items():
        if _contains_any(q, keywords):
            return merchant

    return ""


def _is_follow_up(question: str) -> bool:
    q = question.lower().strip()

    has_follow_up_prefix = any(
        q.startswith(prefix)
        for prefix in FOLLOW_UP_PREFIXES
    )

    has_follow_up_keyword = _contains_any(q, FOLLOW_UP_KEYWORDS)
    has_explicit_category = bool(_infer_category(q))
    has_explicit_merchant = bool(_infer_merchant(q))

    return (
        (has_follow_up_prefix or has_follow_up_keyword)
        and not has_explicit_category
        and not has_explicit_merchant
    )


def _context_to_text(memory: SessionMemory) -> str:
    parts = []

    if memory.last_category:
        parts.append(f"попередня категорія: {memory.last_category}")

    if memory.last_merchant:
        parts.append(f"попередній merchant: {memory.last_merchant}")

    if memory.last_intent:
        parts.append(f"попередній intent: {memory.last_intent}")

    return "; ".join(parts)


def enrich_question_with_memory(question: str, session_id: Optional[str]) -> str:
    """
    Додає контекст до follow-up запитів.

    Приклад:
    1) "Скільки я витрачаю на каву?"
    2) "А за останній місяць?"

    Другий запит стане:
    "А за останній місяць? Контекст попереднього запиту: попередня категорія: coffee"
    """
    if not session_id:
        return question

    memory = _SESSION_MEMORY.get(session_id)

    if not memory:
        return question

    if not _is_follow_up(question):
        return question

    context = _context_to_text(memory)

    if not context:
        return question

    return f"{question}\n\nКонтекст попереднього запиту: {context}."


def remember_turn(
    session_id: Optional[str],
    user_question: str,
    effective_question: str,
    response: AskResponse,
) -> None:
    """
    Зберігає короткий контекст останнього запиту.
    Це in-memory storage: після перезапуску API пам'ять очищується.
    """
    if not session_id:
        return

    memory = _SESSION_MEMORY.get(session_id, SessionMemory())

    memory.last_question = user_question
    memory.last_effective_question = effective_question

    intent = ""
    category = _infer_category(effective_question)
    merchant = _infer_merchant(effective_question)

    for step in response.trace:
        output = step.output

        if isinstance(output, dict) and output.get("intent"):
            intent = output["intent"]

        if isinstance(output, dict):
            tool_result = output.get("tool_result")
            if isinstance(tool_result, dict):
                if tool_result.get("category"):
                    category = str(tool_result["category"])

                if tool_result.get("merchant"):
                    merchant = str(tool_result["merchant"])

    if intent:
        memory.last_intent = intent

    if category:
        memory.last_category = category

    if merchant:
        memory.last_merchant = merchant

    _SESSION_MEMORY[session_id] = memory


def clear_session_memory(session_id: Optional[str]) -> None:
    if session_id:
        _SESSION_MEMORY.pop(session_id, None)