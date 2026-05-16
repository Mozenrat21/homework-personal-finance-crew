# Lesson 11 — Personal Finance Crew

Multi-agent система **Personal Finance Coach** для аналізу фінансових транзакцій користувача.

Проєкт реалізує домашнє завдання Lesson 11 з теми **AI Agents and Tool Orchestration**.

Основна ідея: порівняти дві архітектури:

- `baseline` — single-agent baseline;
- `crew` — multi-agent crew з 3 агентів.

Система працює з наданим файлом `transactions.csv`, не генерує власні дані та не вигадує фінансові показники. Усі числові значення беруться з deterministic pandas tools.

---

## 1. Що реалізовано

У проєкті реалізовано:

- single-agent baseline;
- multi-agent crew з 3 агентів;
- FastAPI endpoint `/ask`;
- Streamlit UI для demo;
- pandas tools для аналізу `transactions.csv`;
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
4. формує відповідь.

Схема:

```text
User question
    ↓
single-agent baseline
    ↓
financial tool
    ↓
answer
```

---

### 2.2. Crew

Crew складається з трьох агентів:

| Agent | Role |
|---|---|
| `router_agent` | визначає intent запиту |
| `data_analyst_agent` | викликає потрібний financial tool |
| `advisor_agent` | формує фінальну відповідь |

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
answer
```

---

## 3. Основні сценарії

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

---

## 4. Дані

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

## 5. Financial tools

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

## 6. Edge cases

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

Для простого deterministic MVP використано stem-like ключі:

```text
кав
достав
```

---

## 7. Структура проєкту

```text
lesson-11-personal-finance-crew/
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

## 8. Встановлення

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 9. Налаштування `.env`

Створи файл `.env` у корені проєкту.

Для EU LangSmith workspace:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=lesson-11-personal-finance-crew
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com

APP_ENV=local
DATA_PATH=app/data/transactions.csv
```

Важливо: `.env` не можна комітити в GitHub.

---

## 10. Запуск FastAPI

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

## 11. Приклад API-запиту

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post -ContentType "application/json" -Body '{"question":"Скільки я витрачаю на каву?","architecture":"crew"}' | ConvertTo-Json -Depth 10
```

Архітектури:

```text
baseline
crew
```

---

## 12. Запуск Streamlit UI

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

## 13. Local evaluation

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

Поточний результат:

| Metric | Baseline | Crew |
|---|---:|---:|
| Total cases | 15 | 15 |
| Success count | 15 | 15 |
| Success rate | 1.0 | 1.0 |
| Tool selection accuracy | 1.0 | 1.0 |
| Groundedness proxy | 1.0 | 1.0 |
| Latency p50, ms | 42.09 | 38.85 |
| Latency p95, ms | 87.83 | 86.82 |
| Avg trace steps | 0.93 | 3.0 |
| Cost per task, USD | 0 | 0 |
| Tokens per task | 0 | 0 |

---

## 14. LangSmith tracing and experiments

Проєкт підтримує LangSmith tracing через `@traceable`.

Tracing підключено для:

- `run_baseline`;
- `run_crew`;
- `router_agent`;
- `data_analyst_agent`;
- `advisor_agent`;
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

Створені experiments:

```text
lesson-11-baseline-91379d20
lesson-11-crew-cafa14dd
```

LangSmith experiments дозволяють дивитися:

- inputs;
- outputs;
- reference outputs;
- evaluator scores;
- traces;
- baseline vs crew comparison.

---

## 15. Результати LangSmith experiments

Після запуску:

```powershell
python -m app.eval.run_langsmith_eval
```

було створено:

```text
Dataset: lesson-11-personal-finance-crew-golden-set
Experiment: lesson-11-baseline-91379d20
Experiment: lesson-11-crew-cafa14dd
```

Це підтверджує, що evaluation працює не тільки локально через CSV, а також через LangSmith UI.

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
router_agent → data_analyst_agent → advisor_agent
```

Для простого deterministic MVP baseline достатній. Для production-системи crew краще масштабується, бо дозволяє окремо розвивати routing, financial analysis, safety та response synthesis.

---

## 17. Обмеження

Поточна реалізація має такі обмеження:

- deterministic rule-based prototype;
- без LLM-викликів;
- cost і tokens дорівнюють 0;
- routing реалізовано через keywords;
- multi-turn memory мінімальна;
- немає persistent user storage;
- немає production authentication.

Це свідомий MVP-підхід: спочатку реалізовано grounded calculations та evaluation, щоб уникнути hallucinations.

---

## 18. Що можна покращити

Можливі покращення:

- додати LLM для natural language understanding;
- додати LangGraph або інший orchestration framework;
- реалізувати persistent memory;
- додати SQLite/Postgres storage;
- додати складніший intent classifier;
- додати cost/tokens metrics для LLM-режиму;
- додати більше golden set cases;
- додати richer Streamlit dashboard;
- додати unit tests.

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

Обидві архітектури успішно пройшли golden set із 15 задач.

Проєкт містить:

- FastAPI API;
- Streamlit demo UI;
- financial tools;
- local eval;
- LangSmith tracing;
- LangSmith dataset and experiments;
- report with comparison.

Ключовий висновок: baseline є простішим і достатнім для MVP, але crew краще підходить для масштабування production AI assistant, бо має прозорий agent trace і розділення відповідальності.
