# Lesson 11 — Personal Finance Crew

## 1. Мета роботи

Мета домашнього завдання — реалізувати multi-agent систему **Personal Finance Coach**, яка відповідає на фінансові запити користувача на основі реальних транзакцій, та порівняти її з **single-agent baseline**.

Система працює з наданим файлом `transactions.csv`, не генерує власні дані та не вигадує фінансові показники. Усі числові значення у відповідях беруться з deterministic pandas tools.

---

## 2. Бізнес-контекст

Уявний замовник — fintech-стартап, який хоче замінити пасивну вкладку з графіками на розмовного фінансового помічника.

Основні очікування:

- відповідь до 10 секунд;
- фінансові поради мають базуватися на реальних транзакціях;
- відповідь має бути actionable, тобто користувач має розуміти, що саме можна зробити;
- підозрілі транзакції не вирішуються агентом самостійно, а ескалюються до підтримки;
- out-of-scope запити, наприклад купівля акцій, відхиляються.

---

## 3. Реалізовані архітектури

У роботі реалізовано дві архітектури:

1. `baseline` — single-agent baseline.
2. `crew` — multi-agent crew з трьох агентів.

---

## 4. Single-agent baseline

Baseline — це один агент, який самостійно:

1. приймає питання користувача;
2. визначає тип запиту через rule-based routing;
3. викликає потрібний financial tool;
4. формує фінальну відповідь.

### Переваги baseline

- простіший код;
- менше orchestration steps;
- легше debug;
- добра швидкість для простих сценаріїв.

### Недоліки baseline

- слабше розділення відповідальності;
- складніше масштабувати логіку;
- менше прозорості у trace;
- складніше окремо розвивати routing, аналіз даних і safety.

---

## 5. Multi-agent crew

Crew складається з трьох спеціалізованих агентів:

| Агент | Роль |
|---|---|
| `router_agent` | визначає intent запиту користувача |
| `data_analyst_agent` | викликає потрібний financial tool |
| `advisor_agent` | формує фінальну відповідь для користувача |

### Flow виконання

```text
User question
    ↓
router_agent
    ↓
data_analyst_agent
    ↓
advisor_agent
    ↓
Answer
```

### Переваги crew

- чітке розділення відповідальності;
- прозорий trace;
- зручніше debug;
- краще масштабується для складнішої production-системи;
- можна окремо розвивати routing, financial analysis, safety та response synthesis.

### Недоліки crew

- складніший код;
- більше orchestration steps;
- більший overhead;
- для простого rule-based MVP не дає суттєвого приросту якості порівняно з baseline.

---

## 6. Дані

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

Категорії в даних:

- `coffee`;
- `credit_payment`;
- `delivery`;
- `entertainment`;
- `groceries`;
- `health`;
- `restaurants`;
- `salary`;
- `shopping`;
- `subscriptions`;
- `transport`;
- `travel`;
- `utilities`.

---

## 7. Реалізовані tools

| Tool | Призначення |
|---|---|
| `dataset_summary` | загальна інформація про датасет |
| `monthly_category_spending` | витрати по категорії в розрізі місяців |
| `top_categories` | топ категорій витрат |
| `last_payment` | останній платіж по merchant |
| `subscriptions_summary` | аналіз підписок і пошук забутих підписок |
| `late_night_delivery_stats` | аналіз доставки після 21:00 |
| `weekend_vs_weekday_stats` | порівняння витрат у будні та вихідні |
| `credit_card_behavior` | аналіз поведінки по кредитній картці |
| `suspicious_transactions` | пошук suspicious транзакцій |
| `simulate_category_reduction` | симуляція економії при скороченні категорії |
| `savings_opportunities` | пошук можливостей для економії |

---

## 8. Приклади підтриманих запитів

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
Як швидше виплатити кредитну картку?
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

## 9. Обробка edge cases

### 9.1. Fraud escalation

Запити щодо підозрілих транзакцій не вирішуються агентом самостійно.

Приклад:

```text
Я не робив транзакцію Booking.com, це шахрайство?
```

Система:

- знаходить suspicious transactions;
- не блокує картку;
- не оформлює chargeback;
- не обіцяє повернення коштів;
- рекомендує звернутися до служби підтримки.

Це важливо, тому що fraud/chargeback — high-risk сценарій, який не повинен автоматично вирішуватися агентом.

---

### 9.2. Out of scope

Запити поза скоупом відхиляються.

Приклад:

```text
Купи мені акції Tesla
```

Відповідь системи пояснює, що агент не може купувати акції, криптовалюту або давати інвестиційні накази. Натомість агент пропонує доступні функції: аналіз витрат, підписок, доставки, кави, кредитної картки та suspicious transactions.

---

### 9.3. Українські відмінки

Під час тестування було знайдено проблему з keyword routing:

```text
кава ≠ каву
доставка ≠ доставку
```

Проблему вирішено через stem-like ключі:

```text
кав
достав
```

Це дозволило коректно обробляти українські форми слів без підключення окремого NLP-модуля.

---

### 9.4. Помилки golden set

Під час evaluation було знайдено помилку у golden set: forbidden phrase `акції` спрацьовувала на слово `транзакції`.

Проблему виправлено заміною надто широкого правила:

```text
акції
```

на конкретніші forbidden phrases:

```text
купити акції
купую акції
купив акції
```

Це важливий висновок: eval також потребує перевірки, бо погані правила можуть створювати false negative.

---

## 10. Golden set

Було створено golden set із 15 тестових задач.

Golden set покриває:

- витрати на каву;
- українські відмінки;
- пошук можливостей економії;
- останній платіж Netflix;
- забуті підписки;
- late-night delivery;
- weekend spike;
- credit card behavior;
- top categories;
- fraud escalation;
- out-of-scope handling;
- simulation сценарій.

Файл golden set:

```text
app/eval/golden_set.json
```

---

## 11. Local evaluation

Локальна evaluation запускається командою:

```powershell
python -m app.eval.run_eval
```

Результати збережено у:

```text
reports/eval_results.csv
reports/eval_summary.json
```

### Підсумкові local eval метрики

| Metric | Baseline | Crew |
|---|---:|---:|
| Total cases | 15 | 15 |
| Success count | 15 | 15 |
| Success rate | 1.0 | 1.0 |
| Tool selection accuracy | 1.0 | 1.0 |
| Groundedness proxy | 1.0 | 1.0 |
| Latency p50, ms | 27.90 | 26.26 |
| Latency p95, ms | 66.19 | 58.39 |
| Avg trace steps | 0.93 | 3.0 |
| Cost per task, USD | 0 | 0 |
| Tokens per task | 0 | 0 |

---

## 12. LangSmith Observability and Experiments

Для observability та evaluation використано LangSmith.

Було підключено tracing через `@traceable` decorators для таких компонентів:

- `run_baseline`;
- `run_crew`;
- `router_agent`;
- `data_analyst_agent`;
- `advisor_agent`;
- tool execution.

Оскільки LangSmith workspace було створено в EU-регіоні, у `.env` використано EU endpoint:

```env
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
```

Без цього tracing повертав `403 Forbidden`, бо запити йшли в default US endpoint.

---

### 12.1. LangSmith Dataset

Створено dataset:

```text
lesson-11-personal-finance-crew-golden-set
```

Dataset містить 15 golden set прикладів.

---

### 12.2. LangSmith Experiments

Було запущено два experiments:

```text
lesson-11-baseline-91379d20
lesson-11-crew-cafa14dd
```

Команда запуску:

```powershell
python -m app.eval.run_langsmith_eval
```

LangSmith experiments дозволяють порівнювати baseline і crew не тільки локально через CSV, а й через UI з:

- inputs;
- outputs;
- reference outputs;
- evaluator scores;
- traces.

---

## 13. Порівняння baseline vs crew

### Baseline

Baseline показав такий самий `success_rate = 1.0`, як і crew. Для простого deterministic MVP baseline є достатнім.

Сильні сторони baseline:

- простіше підтримувати;
- менше кроків;
- менше orchestration overhead;
- швидкий debug.

Слабкі сторони baseline:

- менше прозорості;
- складніше масштабувати;
- routing, tool execution і answer synthesis змішані в одному агенті.

---

### Crew

Crew також показав `success_rate = 1.0`, але має більше trace steps.

Сильні сторони crew:

- краще розділення відповідальності;
- прозорий execution flow;
- зручніше знаходити, на якому етапі виникла помилка;
- краще підходить для production-розширення.

Слабкі сторони crew:

- більша складність;
- більше orchestration steps;
- для простого rule-based MVP якість не вища, ніж у baseline.

---

## 14. Чи виправдане ускладнення multi-agent архітектури

Для поточного rule-based MVP multi-agent архітектура не дала приросту якості, бо обидві архітектури отримали:

```text
success_rate = 1.0
tool_selection_accuracy = 1.0
groundedness_proxy = 1.0
```

Однак multi-agent підхід краще підходить для production-сценарію, якщо в майбутньому додати:

- LLM-based intent routing;
- окремого safety agent;
- memory;
- більше financial tools;
- складніші multi-step сценарії;
- реальний cost/token tracking;
- LangSmith monitoring у production.

Висновок: для простого MVP baseline достатній. Для масштабованої production-системи crew має кращу архітектурну основу.

---

## 15. Обмеження реалізації

Поточна реалізація має такі обмеження:

- LLM не використовується;
- система deterministic rule-based;
- routing реалізовано через keywords;
- multi-turn memory мінімальна;
- cost і tokens дорівнюють 0;
- немає persistent user profiles;
- немає автентифікації;
- немає реального banking API;
- fraud-сценарії тільки ескалюються, але не виконують реальні дії.

Ці обмеження прийняті свідомо, щоб спочатку забезпечити grounded calculations та уникнути hallucinations.

---

## 16. Що можна покращити

Можливі покращення:

1. Додати LLM для flexible intent routing.
2. Додати окремого safety/compliance agent.
3. Додати persistent memory по `session_id`.
4. Додати SQLite/Postgres storage.
5. Додати більше financial scenarios.
6. Додати real token/cost tracking.
7. Додати LLM judge evaluator у LangSmith.
8. Покращити Streamlit UI.
9. Додати Docker.
10. Додати unit tests для tools.

---

## 17. Фінальний висновок

У межах домашнього завдання реалізовано Personal Finance Coach із двома архітектурами:

- `single-agent baseline`;
- `multi-agent crew`.

Система використовує реальні транзакції з `transactions.csv`, виконує точні розрахунки через pandas tools, обробляє fraud escalation та out-of-scope запити.

Обидві архітектури пройшли golden set із 15 задач:

```text
baseline success_rate = 1.0
crew success_rate = 1.0
```

Також підключено LangSmith tracing, створено LangSmith dataset і запущено LangSmith experiments для baseline та crew.

Ключовий висновок: baseline достатній для простого deterministic MVP, але crew краще підходить як архітектурна основа для масштабованого production AI assistant.
