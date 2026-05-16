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

### 2.1. Baseline

Baseline — це один агент, який самостійно:

1. приймає питання користувача;
2. визначає intent;
3. вибирає потрібний tool;
4. формує deterministic fallback answer;
5. передає результат у LLM для фінального answer synthesis;
6. повертає fallback, якщо LLM-відповідь не проходить validation.

Схема:

```text
User question
    ↓
single-agent baseline
    ↓
financial tool
    ↓
deterministic fallback answer
    ↓
OpenRouter LLM answer synthesis
    ↓
validation
    ↓
final answer
```

---

### 2.2. Crew

Crew складається з трьох агентів:

| Agent | Role |
|---|---|
| `router_agent` | визначає intent запиту |
| `data_analyst_agent` | викликає потрібний financial tool |
| `advisor_agent` | формує deterministic fallback answer |

Після цього LLM формулює фінальну відповідь на основі tool result та fallback answer.

Схема:

```text
User question
    ↓
router_agent
    ↓
data_analyst_agent
    ↓
advisor_agent
    ↓
OpenRouter LLM answer synthesis
    ↓
validation
    ↓
final answer
```

---

## 3. LLM answer synthesis

LLM використовується тільки для фінального формулювання відповіді.

Важливо:

- фінансові розрахунки виконує pandas, не LLM;
- LLM не рахує суми самостійно;
- LLM отримує `tool_result` і `deterministic fallback answer`;
- якщо LLM-відповідь втрачає важливі числа або сутності, система повертає deterministic fallback;
- для safety-сценаріїв `fraud_escalation` та `out_of_scope` використовується контрольована поведінка.

Використана модель:

```text
anthropic/claude-3.5-haiku через OpenRouter
```

---

## 4. Основні сценарії

Система вміє відповідати на такі запити:

```text
Скільки я витрачаю на каву?
```

```text
Де можна зекономити $200 цього місяця?
```

```text
Дата останнього платежу за Netflix?
```

```text
Які підписки можуть бути забутими?
```

```text
Скільки витрат на доставку після 21:00?
```

```text
Порівняй витрати у будні та вихідні
```

```text
Як швидше виплатити кредитну картку?
```

```text
Топ-5 категорій витрат
```

```text
Я не робив транзакцію Booking.com, це шахрайство?
```

```text
Якщо зменшити витрати на доставку вдвічі — яка економія за рік?
```

```text
Купи мені акції Tesla
```

---

## 5. Дані

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

Основні категорії:

- `coffee`;
- `delivery`;
- `groceries`;
- `subscriptions`;
- `credit_payment`;
- `restaurants`;
- `shopping`;
- `health`;
- `utilities`;
- `travel`.

---

## 6. Financial tools

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

## 7. Edge cases

### Fraud escalation

Запити щодо fraud або suspicious transactions не вирішуються агентом самостійно.

Приклад:

```text
Я не робив транзакцію Booking.com, це шахрайство?
```

Очікувана поведінка:

- знайти suspicious transactions;
- не обіцяти повернення коштів;
- не оформлювати chargeback;
- направити користувача до служби підтримки.

---

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

---

### Ukrainian keyword routing

Під час тестування було знайдено проблему з українськими відмінками:

```text
кава ≠ каву
доставка ≠ доставку
```

Для простого MVP використано stem-like ключі:

```text
кав
достав
```

---

## 8. Структура проєкту

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
│   ├── __init__.py
│   ├── config.py
│   ├── llm.py
│   ├── main.py
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

## 9. Встановлення

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 10. Налаштування `.env`

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

# App
APP_ENV=local
DATA_PATH=app/data/transactions.csv
```

Важливо: `.env` не можна комітити в GitHub.

---

## 11. Запуск FastAPI

```powershell
python -m uvicorn app.main:app --reload
```

Health check:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
```

Очікувано:

```text
status service
------ -------
ok     personal-finance-crew
```

---

## 12. Приклад API-запиту

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post -ContentType "application/json" -Body '{"question":"Де можна зекономити $200 цього місяця?","architecture":"crew"}' | ConvertTo-Json -Depth 10
```

Архітектури:

```text
baseline
crew
```

---

## 13. Запуск Streamlit UI

В окремому терміналі:

```powershell
streamlit run streamlit_app.py
```

Після запуску відкрити:

```text
http://localhost:8501
```

У UI можна:

- ввести питання;
- вибрати `baseline` або `crew`;
- подивитися відповідь;
- розкрити trace;
- запустити smoke eval.

---

## 14. Local evaluation

Golden set містить 15 тестових задач.

Запуск:

```powershell
python -m app.eval.run_eval
```

Файли результатів:

```text
reports/eval_results.csv
reports/eval_summary.json
```

Поточний результат з LLM answer synthesis:

| Metric | Baseline | Crew |
|---|---:|---:|
| Total cases | 15 | 15 |
| Success count | 15 | 15 |
| Success rate | 1.0 | 1.0 |
| Tool selection accuracy | 1.0 | 1.0 |
| Groundedness proxy | 1.0 | 1.0 |
| Latency p50, ms | 3894.46 | 3931.89 |
| Latency p95, ms | 5843.68 | 6077.31 |
| Avg trace steps | 0.93 | 3.0 |
| Tokens per task | 818.2 | 688.67 |
| Cost per task, USD | 0.0 | 0.0 |

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

---

### LangSmith dataset

Створюється dataset:

```text
lesson-11-personal-finance-crew-golden-set
```

---

### LangSmith experiments

Запуск:

```powershell
python -m app.eval.run_langsmith_eval
```

Створені experiments з LLM answer synthesis:

```text
lesson-11-baseline-9c86df00
lesson-11-crew-f4e8cf79
```

LangSmith experiments дозволяють дивитися:

- inputs;
- outputs;
- reference outputs;
- evaluator scores;
- traces;
- baseline vs crew comparison.

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

Для простого MVP baseline достатній. Для production-системи crew краще масштабується, бо дозволяє окремо розвивати routing, financial analysis, safety та response synthesis.

---

## 17. Обмеження

Поточна реалізація має такі обмеження:

- routing реалізовано через keywords;
- multi-turn memory мінімальна;
- немає persistent user storage;
- немає production authentication;
- немає реального banking API;
- cost у local eval не рахується локально, бо залежить від OpenRouter billing/model pricing.

При цьому фінансові розрахунки grounded: усі суми беруться з `transactions.csv` через pandas tools.

---

## 18. Що можна покращити

Можливі покращення:

- додати LangGraph або інший orchestration framework;
- реалізувати persistent memory;
- додати SQLite/Postgres storage;
- додати складніший intent classifier;
- додати cost calculation для OpenRouter;
- додати більше golden set cases;
- додати richer Streamlit dashboard;
- додати unit tests для tools;
- додати окремого safety/compliance agent.

---

## 19. Команди для фінальної перевірки

```powershell
python -m app.eval.run_eval
```

```powershell
python -m app.eval.run_langsmith_eval
```

```powershell
streamlit run streamlit_app.py
```

```powershell
python -m uvicorn app.main:app --reload
```

---

## 20. Висновок

У межах ДЗ реалізовано Personal Finance Coach з двома архітектурами:

- single-agent baseline;
- multi-agent crew.

Проєкт містить:

- FastAPI API;
- Streamlit demo UI;
- financial tools;
- OpenRouter LLM answer synthesis;
- validation fallback;
- local eval;
- LangSmith tracing;
- LangSmith dataset and experiments;
- report with comparison.

Ключовий висновок: baseline є простішим і достатнім для MVP, але crew краще підходить для масштабування production AI assistant, бо має прозорий agent trace і розділення відповідальності.
