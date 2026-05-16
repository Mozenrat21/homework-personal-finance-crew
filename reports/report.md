# Lesson 11 — Personal Finance Crew

## 1. Мета роботи

Мета домашнього завдання — реалізувати multi-agent систему **Personal Finance Coach**, яка відповідає на фінансові запити користувача на основі реальних транзакцій, та порівняти її з **single-agent baseline**.

Система має показати:

- як працює single-agent baseline;
- як працює multi-agent crew;
- у яких випадках multi-agent архітектура корисна;
- у яких випадках вона створює зайвий overhead;
- чи виправдане ускладнення для production-сценарію.

У фінальному варіанті додано:

- LLM answer synthesis через OpenRouter;
- validation fallback;
- simple in-memory session memory;
- token usage tracking;
- cost estimation.

Усі фінансові розрахунки виконуються deterministic pandas tools.

---

## 2. Бізнес-контекст

Уявний замовник — fintech-стартап, який хоче замінити пасивну вкладку з графіками на розмовного фінансового помічника.

Основні очікування:

- відповідь до 10 секунд;
- фінансові поради мають базуватися на реальних транзакціях;
- відповідь має бути actionable;
- підозрілі транзакції не вирішуються агентом самостійно, а ескалюються до підтримки;
- out-of-scope запити, наприклад купівля акцій, відхиляються;
- система має давати базовий multi-turn context для follow-up питань.

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

Переваги:

- простіший код;
- менше orchestration steps;
- легше debug;
- хороша швидкість для простих сценаріїв.

Недоліки:

- слабше розділення відповідальності;
- складніше масштабувати логіку;
- routing, tool execution і answer synthesis змішані в одному агенті;
- менше прозорості у trace порівняно з crew.

---

## 6. Multi-agent crew

Crew складається з трьох спеціалізованих агентів:

| Агент | Роль |
|---|---|
| `router_agent` | визначає intent запиту користувача |
| `data_analyst_agent` | викликає потрібний financial tool |
| `advisor_agent` | формує deterministic fallback answer |

Flow виконання:

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

Переваги:

- чітке розділення відповідальності;
- прозорий trace;
- зручніше debug;
- краще масштабується для production-системи.

Недоліки:

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
- якщо LLM-відповідь втрачає важливі числа, сутності або валюту, система повертає deterministic fallback;
- якщо LLM-відповідь відхилена validator-ом, cost усе одно враховується, бо LLM-виклик уже відбувся;
- для safety intents `fraud_escalation` та `out_of_scope` використовується контрольована поведінка.

---

## 8. Cost estimation

Cost estimation реалізовано локально на основі token usage.

Формула:

```text
cost = input_tokens / 1_000_000 * input_price_per_1M
     + output_tokens / 1_000_000 * output_price_per_1M
```

Для `anthropic/claude-3.5-haiku` використано:

```env
OPENROUTER_INPUT_PRICE_PER_1M=0.80
OPENROUTER_OUTPUT_PRICE_PER_1M=4.00
```

Приклад одиничного API-запиту після додавання cost tracking:

```text
tokens = 916
cost_usd = 0.0013248
```

Якщо LLM-відповідь rejected validator-ом, cost усе одно враховується, бо API-виклик уже був виконаний.

---

## 9. Multi-turn memory

Додано просту in-memory session memory.

Приклад:

```text
User: Скільки я витрачаю на каву?
Assistant: ... відповідь про coffee ...

User: А за останній місяць?
Assistant: ... продовжує відповідати в контексті coffee ...
```

Реалізація:

- використовується `session_id`;
- система запам’ятовує останній intent/category/merchant;
- follow-up запит отримує попередній контекст;
- пам’ять очищується після перезапуску API.

Це MVP-рівень memory без persistent storage.

---

## 10. Реалізовані tools

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

## 11. Edge cases

### Fraud escalation

Запити щодо підозрілих транзакцій не вирішуються агентом самостійно.

Система:

- знаходить suspicious transactions;
- не блокує картку;
- не оформлює chargeback;
- не обіцяє повернення коштів;
- рекомендує звернутися до служби підтримки.

### Out of scope

Запити поза скоупом відхиляються.

Приклад:

```text
Купи мені акції Tesla
```

Система пояснює, що агент не може купувати акції, криптовалюту або давати інвестиційні накази.

### Follow-up false positive

Після додавання memory було знайдено проблему: слово `а` всередині фрази могло помилково вмикати follow-up context.

Проблему виправлено:

- prefix follow-up markers перевіряються тільки на початку запиту;
- явні категорії `будні`, `вихідні`, `weekend` не вважаються follow-up без контексту.

### Currency guard

LLM іноді міг замінити `$` на `грн`. Це було виправлено через:

- prompt rule: dataset currency is USD;
- validation rule: якщо fallback містить `$`, LLM не може повернути `грн` або `UAH`.

---

## 12. Golden set

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

## 13. Local evaluation

Локальна evaluation запускається командою:

```powershell
python -m app.eval.run_eval
```

Результати збережено у:

```text
reports/eval_results.csv
reports/eval_summary.json
```

Підсумкові local eval метрики з LLM answer synthesis, memory та cost estimation:

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

Інтерпретація:

```text
baseline success_rate = 1.0
crew success_rate = 1.0
latency_p95 < 10000 ms
```

Cost per task тепер явно вимірюється та потрапляє у `eval_summary.json`.

---

## 14. LangSmith Observability and Experiments

Для observability та evaluation використано LangSmith.

Tracing підключено через `@traceable` decorators для таких компонентів:

- `run_baseline`;
- `run_crew`;
- `router_agent`;
- `data_analyst_agent`;
- `advisor_agent`;
- `openrouter_answer_synthesizer`;
- tool execution.

EU endpoint:

```env
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
```

Dataset:

```text
lesson-11-personal-finance-crew-golden-set
```

Команда запуску:

```powershell
python -m app.eval.run_langsmith_eval
```

Команда створює experiments для baseline та crew. Після фінального запуску можна додати конкретні experiment names у текст здачі.

---

## 15. Порівняння baseline vs crew

Для поточного MVP multi-agent архітектура не дала приросту success rate, бо обидві архітектури отримали:

```text
success_rate = 1.0
tool_selection_accuracy = 1.0
groundedness_proxy = 1.0
```

Baseline простіший і дешевший для підтримки.

Crew краще підходить для production-сценарію, якщо в майбутньому додати:

- складніший LLM-based intent routing;
- окремого safety/compliance agent;
- persistent memory;
- більше financial tools;
- складніші multi-step сценарії;
- real billing reconciliation;
- LangSmith monitoring у production.

---

## 16. Обмеження реалізації

Поточна реалізація має такі обмеження:

- routing реалізовано через keywords;
- multi-turn memory реалізована мінімально через in-memory session context;
- після перезапуску API пам’ять очищується;
- cost estimation — це локальна оцінка, а не офіційний OpenRouter invoice;
- немає persistent user profiles;
- немає автентифікації;
- немає реального banking API;
- fraud-сценарії тільки ескалюються, але не виконують реальні дії.

---

## 17. Фінальний висновок

У межах домашнього завдання реалізовано Personal Finance Coach із двома архітектурами:

- `single-agent baseline`;
- `multi-agent crew`.

Система використовує реальні транзакції з `transactions.csv`, виконує точні розрахунки через pandas tools, застосовує LLM answer synthesis через OpenRouter, рахує token usage і cost estimate, підтримує простий multi-turn context, обробляє fraud escalation та out-of-scope запити.

Обидві архітектури пройшли golden set із 15 задач:

```text
baseline success_rate = 1.0
crew success_rate = 1.0
```

Ключовий висновок: baseline достатній для простого MVP, але crew краще підходить як архітектурна основа для масштабованого production AI assistant.
