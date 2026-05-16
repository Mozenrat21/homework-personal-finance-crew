# Lesson 11 — Personal Finance Crew

## 1. Мета роботи

Мета домашнього завдання — реалізувати multi-agent систему **Personal Finance Coach**, яка відповідає на фінансові запити користувача на основі реальних транзакцій, та порівняти її з **single-agent baseline**.

Система має показати:

- як працює single-agent baseline;
- як працює multi-agent crew;
- у яких випадках multi-agent архітектура корисна;
- у яких випадках вона створює зайвий overhead;
- чи виправдане ускладнення для production-сценарію.

У фінальному варіанті додано LLM answer synthesis через OpenRouter, але всі фінансові розрахунки виконуються deterministic pandas tools.

---

## 2. Бізнес-контекст

Уявний замовник — fintech-стартап, який хоче замінити пасивну вкладку з графіками на розмовного фінансового помічника.

Основні очікування:

- відповідь до 10 секунд;
- фінансові поради мають базуватися на реальних транзакціях;
- відповідь має бути actionable;
- підозрілі транзакції не вирішуються агентом самостійно, а ескалюються до підтримки;
- out-of-scope запити, наприклад купівля акцій, відхиляються.

---

## 3. Дані

Система використовує наданий файл:

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

Категорії:

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

## 4. Реалізовані архітектури

У роботі реалізовано дві архітектури:

1. `baseline` — single-agent baseline.
2. `crew` — multi-agent crew з трьох агентів.

---

## 5. Single-agent baseline

Baseline — це один агент, який самостійно:

1. приймає питання користувача;
2. визначає тип запиту через rule-based routing;
3. викликає потрібний financial tool;
4. формує deterministic fallback answer;
5. передає відповідь у LLM answer synthesis;
6. повертає fallback, якщо LLM-відповідь не проходить validation.

### Переваги baseline

- простіший код;
- менше orchestration steps;
- легше debug;
- хороша швидкість для простих сценаріїв.

### Недоліки baseline

- слабше розділення відповідальності;
- складніше масштабувати логіку;
- routing, tool execution і answer synthesis сильніше змішані;
- менше прозорості у trace порівняно з crew.

---

## 6. Multi-agent crew

Crew складається з трьох спеціалізованих агентів:

| Агент | Роль |
|---|---|
| `router_agent` | визначає intent запиту користувача |
| `data_analyst_agent` | викликає потрібний financial tool |
| `advisor_agent` | формує deterministic fallback answer |

Після цього відповідь передається в LLM answer synthesis.

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
openrouter_answer_synthesizer
    ↓
validation
    ↓
final answer
```

### Переваги crew

- чітке розділення відповідальності;
- прозорий trace;
- зручніше debug;
- краще масштабується для production-системи;
- можна окремо розвивати routing, financial analysis, safety та response synthesis.

### Недоліки crew

- складніший код;
- більше orchestration steps;
- більший overhead;
- для простого MVP якість не вища, ніж у baseline.

---

## 7. LLM answer synthesis

У фінальній версії додано LLM-шар через OpenRouter.

Використана модель:

```text
anthropic/claude-3.5-haiku
```

LLM використовується тільки для фінального формулювання відповіді.

Важливо:

- LLM не рахує суми самостійно;
- усі числа беруться з deterministic pandas tools;
- LLM отримує `tool_result` і `deterministic fallback answer`;
- якщо LLM-відповідь втрачає важливі числа або сутності, система повертає deterministic fallback;
- для safety intents `fraud_escalation` та `out_of_scope` використовується контрольована поведінка.

### Навіщо потрібен fallback

Фінансові відповіді не можуть базуватися на здогадках моделі. Тому система перевіряє, чи LLM зберіг важливі числа, merchant names та категорії.

Якщо модель втратила критичну інформацію, відповідь відхиляється.

---

## 8. Реалізовані tools

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

## 9. Підтримані сценарії

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
Я не робив транзакцію Booking.com, це шахрайство?
```

```text
Якщо зменшити витрати на доставку вдвічі — яка економія за рік?
```

```text
Купи мені акції Tesla
```

---

## 10. Edge cases

### 10.1. Fraud escalation

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

Це важливо, тому що fraud/chargeback — high-risk сценарій.

---

### 10.2. Out of scope

Запити поза скоупом відхиляються.

Приклад:

```text
Купи мені акції Tesla
```

Відповідь системи пояснює, що агент не може купувати акції, криптовалюту або давати інвестиційні накази.

---

### 10.3. Українські відмінки

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

---

### 10.4. Помилки golden set

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

## 11. Golden set

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

## 12. Local evaluation

Локальна evaluation запускається командою:

```powershell
python -m app.eval.run_eval
```

Результати збережено у:

```text
reports/eval_results.csv
reports/eval_summary.json
```

### Підсумкові local eval метрики з LLM answer synthesis

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

### Інтерпретація метрик

Обидві архітектури пройшли golden set повністю:

```text
baseline success_rate = 1.0
crew success_rate = 1.0
```

Обидві архітектури також залишилися в межах SLA:

```text
latency_p95 < 10000 ms
```

Crew має більше trace steps, але дає кращу прозорість процесу.

---

## 13. LangSmith Observability and Experiments

Для observability та evaluation використано LangSmith.

Було підключено tracing через `@traceable` decorators для таких компонентів:

- `run_baseline`;
- `run_crew`;
- `router_agent`;
- `data_analyst_agent`;
- `advisor_agent`;
- `openrouter_answer_synthesizer`;
- tool execution.

Оскільки LangSmith workspace було створено в EU-регіоні, у `.env` використано EU endpoint:

```env
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
```

---

### 13.1. LangSmith Dataset

Створено dataset:

```text
lesson-11-personal-finance-crew-golden-set
```

Dataset містить 15 golden set прикладів.

---

### 13.2. LangSmith Experiments

Було запущено два experiments з LLM answer synthesis:

```text
lesson-11-baseline-9c86df00
lesson-11-crew-f4e8cf79
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

## 14. Порівняння baseline vs crew

### Baseline

Baseline показав такий самий `success_rate = 1.0`, як і crew.

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
- для простого MVP якість не вища, ніж у baseline.

---

## 15. Чи виправдане ускладнення multi-agent архітектури

Для поточного MVP multi-agent архітектура не дала приросту success rate, бо обидві архітектури отримали:

```text
success_rate = 1.0
tool_selection_accuracy = 1.0
groundedness_proxy = 1.0
```

Однак multi-agent підхід краще підходить для production-сценарію, якщо в майбутньому додати:

- складніший LLM-based intent routing;
- окремого safety/compliance agent;
- memory;
- більше financial tools;
- складніші multi-step сценарії;
- real cost calculation;
- LangSmith monitoring у production.

Висновок: для простого MVP baseline достатній. Для масштабованої production-системи crew має кращу архітектурну основу.

---

## 16. Обмеження реалізації

Поточна реалізація має такі обмеження:

- routing реалізовано через keywords;
- multi-turn memory мінімальна;
- cost у local eval не розраховується на основі реального OpenRouter billing;
- немає persistent user profiles;
- немає автентифікації;
- немає реального banking API;
- fraud-сценарії тільки ескалюються, але не виконують реальні дії.

Ці обмеження прийняті свідомо, щоб спочатку забезпечити grounded calculations та уникнути hallucinations.

---

## 17. Що можна покращити

Можливі покращення:

1. Додати LangGraph або інший orchestration framework.
2. Додати окремого safety/compliance agent.
3. Додати persistent memory по `session_id`.
4. Додати SQLite/Postgres storage.
5. Додати більше financial scenarios.
6. Додати real OpenRouter cost calculation.
7. Додати LLM judge evaluator у LangSmith.
8. Покращити Streamlit UI.
9. Додати Docker.
10. Додати unit tests для tools.

---

## 18. Фінальний висновок

У межах домашнього завдання реалізовано Personal Finance Coach із двома архітектурами:

- `single-agent baseline`;
- `multi-agent crew`.

Система використовує реальні транзакції з `transactions.csv`, виконує точні розрахунки через pandas tools, застосовує LLM answer synthesis через OpenRouter, обробляє fraud escalation та out-of-scope запити.

Обидві архітектури пройшли golden set із 15 задач:

```text
baseline success_rate = 1.0
crew success_rate = 1.0
```

Також підключено LangSmith tracing, створено LangSmith dataset і запущено LangSmith experiments для baseline та crew.

Ключовий висновок: baseline достатній для простого MVP, але crew краще підходить як архітектурна основа для масштабованого production AI assistant.
