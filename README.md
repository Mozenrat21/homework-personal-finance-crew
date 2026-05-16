# Lesson 11 — Personal Finance Crew

Multi-agent система **Personal Finance Coach** для аналізу фінансових транзакцій користувача.

Проєкт реалізує домашнє завдання Lesson 11 з теми **AI Agents and Tool Orchestration**.

Основна мета: порівняти дві архітектури:

- `baseline` — single-agent baseline;
- `crew` — multi-agent crew з 3 спеціалізованих агентів.

Система працює з наданим файлом `transactions.csv`, не генерує власні дані та не вигадує фінансові показники. Усі фінансові розрахунки виконуються deterministic pandas tools, а LLM використовується тільки для фінального формулювання відповіді.

---

## 1. Що реалізовано

У проєкті реалізовано:

- single-agent baseline;
- multi-agent crew з 3 агентів;
- pandas tools для аналізу `transactions.csv`;
- LLM answer synthesis через OpenRouter;
- модель `anthropic/claude-3.5-haiku`;
- validation/fallback для захисту від hallucinations;
- simple in-memory session context для follow-up questions;
- LLM token usage tracking;
- LLM cost estimation на основі token usage;
- FastAPI endpoint `/ask`;
- Streamlit UI для demo;
- golden set із 15 тестових задач;
- local evaluation baseline vs crew;
- LangSmith tracing;
- LangSmith dataset and experiments;
- fraud escalation;
- out-of-scope handling.

---

## 2. Архітектури

### Baseline

Baseline — це один агент, який самостійно:

1. приймає питання користувача;
2. визначає intent;
3. вибирає потрібний tool;
4. формує deterministic fallback answer;
5. передає результат у LLM для фінального answer synthesis;
6. повертає fallback, якщо LLM-відповідь не проходить validation.

```text
User question → single-agent baseline → financial tool → fallback answer → OpenRouter LLM → validation → final answer
```

### Crew

Crew складається з трьох агентів:

| Agent | Role |
|---|---|
| `router_agent` | визначає intent запиту |
| `data_analyst_agent` | викликає потрібний financial tool |
| `advisor_agent` | формує deterministic fallback answer |

```text
User question → router_agent → data_analyst_agent → advisor_agent → OpenRouter LLM → validation → final answer
```

---

## 3. LLM answer synthesis

LLM використовується тільки для фінального формулювання відповіді.

Важливо:

- фінансові розрахунки виконує pandas, не LLM;
- LLM не рахує суми самостійно;
- LLM отримує `tool_result` і `deterministic fallback answer`;
- якщо LLM-відповідь втрачає важливі числа, сутності або валюту, система повертає deterministic fallback;
- якщо LLM-відповідь відхилена validator-ом, tokens і cost все одно враховуються, бо API-виклик уже відбувся;
- для safety-сценаріїв `fraud_escalation` та `out_of_scope` використовується контрольована поведінка.

Використана модель:

```text
anthropic/claude-3.5-haiku через OpenRouter
```

---

## 4. Cost estimation

Cost estimation рахується локально на основі token usage:

```text
cost = input_tokens / 1_000_000 * input_price_per_1M
     + output_tokens / 1_000_000 * output_price_per_1M
```

Ціни задаються через `.env`:

```env
OPENROUTER_INPUT_PRICE_PER_1M=0.80
OPENROUTER_OUTPUT_PRICE_PER_1M=4.00
```

Це estimate, а не фінальний invoice. Фактичний billing може відрізнятися залежно від OpenRouter provider, моделі та тарифів.

---

## 5. Multi-turn memory

Додано просту in-memory session memory для follow-up запитів.

Приклад:

```text
User: Скільки я витрачаю на каву?
Assistant: ... відповідь про coffee ...

User: А за останній місяць?
Assistant: ... продовжує відповідати в контексті coffee ...
```

Технічно це працює через `session_id`. Якщо запит схожий на follow-up і не містить нової явної категорії, система додає попередній контекст до effective question.

Важливо: пам’ять in-memory, тобто після перезапуску API вона очищується.

---

## 6. Основні сценарії

Система вміє відповідати на такі запити:

```text
Скільки я витрачаю на каву?
А за останній місяць?
Де можна зекономити $200 цього місяця?
Дата останнього платежу за Netflix?
Які підписки можуть бути забутими?
Скільки витрат на доставку після 21:00?
Порівняй витрати у будні та вихідні
Як швидше виплатити кредитну картку?
Топ-5 категорій витрат
Я не робив транзакцію Booking.com, це шахрайство?
Якщо зменшити витрати на доставку вдвічі — яка економія за рік?
Купи мені акції Tesla
```

---

## 7. Дані

Система використовує файл:

```text
app/data/transactions.csv
```

Датасет містить:

| Показник | Значення |
|---|---:|
| Кількість транзакцій | 842 |
| Період | 2024-12-01 — 2025-11-30 |
| Валюта | USD |
| Загальні витрати | 29090.45 |
| Загальний дохід | 28800.0 |

---

## 8. Financial tools

| Tool | Призначення |
|---|---|
| `dataset_summary` | загальна інформація про dataset |
| `category_spending` | витрати по категорії за період |
| `monthly_category_spending` | витрати по категорії в розрізі місяців |
| `top_categories` | топ категорій витрат |
| `last_payment` | останній платіж по merchant |
| `subscriptions_summary` | аналіз підписок |
| `late_night_delivery_stats` | аналіз доставки після 21:00 |
| `weekend_vs_weekday_stats` | порівняння буднів і вихідних |
| `credit_card_behavior` | аналіз кредитної картки |
| `suspicious_transactions` | пошук suspicious транзакцій |
| `simulate_category_reduction` | симуляція економії |
| `savings_opportunities` | пошук можливостей економії |

---

## 9. Edge cases

### Fraud escalation

Запити щодо fraud або suspicious transactions не вирішуються агентом самостійно.

Очікувана поведінка:

- знайти suspicious transactions;
- не обіцяти повернення коштів;
- не оформлювати chargeback;
- направити користувача до служби підтримки.

### Out of scope

Запити поза скоупом відхиляються.

Приклад:

```text
Купи мені акції Tesla
```

Очікувана поведінка:

- агент не купує акції;
- не дає інвестиційних наказів;
- пояснює, які фінансові аналітичні задачі він може виконувати.

### Currency guard

LLM не має права замінювати `$` на `грн` або `UAH`, бо датасет у USD. Якщо LLM змінює валюту, відповідь відхиляється і повертається fallback.

---

## 10. Структура проєкту

```text
homework-personal-finance-crew/
├── app/
│   ├── agents/
│   │   ├── baseline_agent.py
│   │   └── crew_agent.py
│   ├── data/
│   │   └── transactions.csv
│   ├── eval/
│   │   ├── golden_set.json
│   │   ├── run_eval.py
│   │   └── run_langsmith_eval.py
│   ├── tools/
│   │   └── finance_tools.py
│   ├── config.py
│   ├── llm.py
│   ├── main.py
│   ├── memory.py
│   ├── schemas.py
│   └── tracing.py
├── reports/
│   ├── eval_results.csv
│   ├── eval_summary.json
│   └── report.md
├── streamlit_app.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 11. Встановлення

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 12. Налаштування `.env`

Створи файл `.env` у корені проєкту.

```env
# LangSmith
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key_here
LANGSMITH_PROJECT=lesson-11-personal-finance-crew
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com

# OpenRouter LLM
USE_LLM=true
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3.5-haiku
OPENROUTER_SITE_URL=http://localhost:8000
OPENROUTER_APP_NAME=Lesson 11 Personal Finance Crew

# Cost estimation for selected OpenRouter model
OPENROUTER_INPUT_PRICE_PER_1M=0.80
OPENROUTER_OUTPUT_PRICE_PER_1M=4.00

# App
APP_ENV=local
DATA_PATH=app/data/transactions.csv
```

Важливо: `.env` не можна комітити в GitHub.

---

## 13. Запуск

FastAPI:

```powershell
python -m uvicorn app.main:app --reload
```

Streamlit:

```powershell
streamlit run streamlit_app.py
```

Local eval:

```powershell
python -m app.eval.run_eval
```

LangSmith eval:

```powershell
python -m app.eval.run_langsmith_eval
```

---

## 14. Local evaluation

Golden set містить 15 тестових задач.

Поточний результат з LLM answer synthesis, memory та cost estimation:

| Metric | Baseline | Crew |
|---|---:|---:|
| Total cases | 15 | 15 |
| Success count | 15 | 15 |
| Success rate | 1.0 | 1.0 |
| Tool selection accuracy | 1.0 | 1.0 |
| Groundedness proxy | 1.0 | 1.0 |
| Latency p50, ms | 3437.29 | 3448.24 |
| Latency p95, ms | 5281.46 | 5430.94 |
| Avg trace steps | 0.93 | 3.0 |
| Tokens per task | 874.27 | 743.47 |
| Cost per task, USD | 0.00109323 | 0.00094997 |

---

## 15. LangSmith tracing and experiments

Проєкт підтримує LangSmith tracing через `@traceable`.

Tracing підключено для:

- `run_baseline`;
- `run_crew`;
- `router_agent`;
- `data_analyst_agent`;
- `advisor_agent`;
- `openrouter_answer_synthesizer`;
- tool execution.

Для EU workspace використовується endpoint:

```text
https://eu.api.smith.langchain.com
```

Dataset:

```text
lesson-11-personal-finance-crew-golden-set
```

Команда `python -m app.eval.run_langsmith_eval` створює experiments для baseline і crew у LangSmith. Після фінального прогону можна вказати конкретні experiment names у тексті здачі.

---

## 16. Інтерпретація результатів

Обидві архітектури успішно пройшли golden set:

```text
success_rate = 1.0
tool_selection_accuracy = 1.0
groundedness_proxy = 1.0
```

Baseline простіший і має менше orchestration steps.

Crew має більший orchestration overhead, але краще показує процес прийняття рішення:

```text
router_agent → data_analyst_agent → advisor_agent → openrouter_answer_synthesizer
```

Для простого MVP baseline достатній. Для production-системи crew краще масштабується, бо дозволяє окремо розвивати routing, financial analysis, safety, memory та response synthesis.

---

## 17. Обмеження

Поточна реалізація має такі обмеження:

- routing реалізовано через keywords;
- multi-turn memory реалізована мінімально через in-memory session context;
- після перезапуску API session memory очищується;
- немає persistent user storage;
- немає production authentication;
- немає реального banking API;
- cost у local eval розраховується як estimate на основі token usage і цін із `.env`; фактичний billing може відрізнятися від OpenRouter invoice.

---

## 18. Висновок

У межах ДЗ реалізовано Personal Finance Coach з двома архітектурами:

- single-agent baseline;
- multi-agent crew.

Проєкт містить:

- FastAPI API;
- Streamlit demo UI;
- financial tools;
- OpenRouter LLM answer synthesis;
- validation fallback;
- in-memory session context;
- local eval;
- cost estimation;
- LangSmith tracing;
- LangSmith dataset and experiments.

Ключовий висновок: baseline є простішим і достатнім для MVP, але crew краще підходить для масштабування production AI assistant, бо має прозорий agent trace і розділення відповідальності.
