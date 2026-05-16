from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Any

import pandas as pd


DEFAULT_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "transactions.csv"


CATEGORY_ALIASES = {
    "кава": "coffee",
    "coffee": "coffee",
    "кав": "coffee",

    "доставка": "delivery",
    "delivery": "delivery",
    "glovo": "delivery",
    "bolt food": "delivery",
    "uber eats": "delivery",

    "підписки": "subscriptions",
    "підписка": "subscriptions",
    "subscriptions": "subscriptions",
    "subscription": "subscriptions",

    "продукти": "groceries",
    "groceries": "groceries",
    "їжа": "groceries",

    "ресторани": "restaurants",
    "restaurants": "restaurants",
    "restaurant": "restaurants",

    "транспорт": "transport",
    "transport": "transport",

    "розваги": "entertainment",
    "entertainment": "entertainment",

    "покупки": "shopping",
    "shopping": "shopping",

    "здоров'я": "health",
    "здоровя": "health",
    "health": "health",

    "комунальні": "utilities",
    "utilities": "utilities",

    "зарплата": "salary",
    "salary": "salary",

    "кредит": "credit_payment",
    "кредитна карта": "credit_payment",
    "credit": "credit_payment",
    "credit_payment": "credit_payment",

    "подорожі": "travel",
    "travel": "travel",
}


def get_data_path() -> Path:
    """
    Беремо шлях до CSV з DATA_PATH, якщо він заданий у .env.
    Якщо ні — використовуємо app/data/transactions.csv.
    """
    return Path(os.getenv("DATA_PATH", DEFAULT_DATA_PATH))


def normalize_category(category: str) -> str:
    """
    Перетворює людський текст у назву категорії з CSV.
    Наприклад: 'кава' -> 'coffee'.
    """
    value = category.strip().lower()
    return CATEGORY_ALIASES.get(value, value)


def load_transactions(data_path: Optional[str | Path] = None) -> pd.DataFrame:
    """
    Завантажує transactions.csv і додає технічні поля для аналізу.
    """
    path = Path(data_path) if data_path else get_data_path()

    if not path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {path}. "
            f"Перевір, що файл лежить у app/data/transactions.csv"
        )

    df = pd.read_csv(path)

    required_columns = {
        "date",
        "merchant",
        "amount",
        "currency",
        "category",
        "account",
        "recurring",
    }

    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing columns in CSV: {sorted(missing_columns)}")

    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df["amount"] = pd.to_numeric(df["amount"], errors="raise")

    df["recurring"] = (
        df["recurring"]
        .astype(str)
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    df["is_expense"] = df["amount"] < 0
    df["expense_amount"] = df["amount"].where(df["amount"] < 0, 0).abs()

    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["year"] = df["date"].dt.year
    df["weekday"] = df["date"].dt.weekday
    df["is_weekend"] = df["weekday"] >= 5
    df["hour"] = df["date"].dt.hour

    return df


def filter_period(
    df: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Фільтр за періодом.
    end_date трактуємо включно: якщо передали 2025-06-30,
    то беремо весь день 30 червня.
    """
    result = df.copy()

    if start_date:
        start = pd.to_datetime(start_date)
        result = result[result["date"] >= start]

    if end_date:
        end = pd.to_datetime(end_date) + pd.Timedelta(days=1)
        result = result[result["date"] < end]

    return result


def to_records(df: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    """
    Безпечний JSON-friendly формат для повернення транзакцій.
    """
    output = df.head(limit).copy()
    output["date"] = output["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return output.to_dict(orient="records")


def dataset_summary() -> dict[str, Any]:
    """
    Загальна перевірка dataset.
    Потрібно для README і debug.
    """
    df = load_transactions()

    return {
        "rows": int(len(df)),
        "date_min": str(df["date"].min()),
        "date_max": str(df["date"].max()),
        "currency": sorted(df["currency"].dropna().unique().tolist()),
        "categories": sorted(df["category"].dropna().unique().tolist()),
        "expense_total": round(float(df["expense_amount"].sum()), 2),
        "income_total": round(float(df.loc[df["amount"] > 0, "amount"].sum()), 2),
    }


def category_spending(
    category: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    """
    Рахує витрати по категорії за період.
    Приклад: category='coffee', start_date='2025-06-01', end_date='2025-06-30'
    """
    df = load_transactions()
    normalized_category = normalize_category(category)

    period_df = filter_period(df, start_date, end_date)
    expenses = period_df[
        (period_df["is_expense"])
        & (period_df["category"] == normalized_category)
    ]

    merchants = (
        expenses.groupby("merchant")["expense_amount"]
        .sum()
        .sort_values(ascending=False)
        .round(2)
        .to_dict()
    )

    return {
        "category": normalized_category,
        "start_date": start_date,
        "end_date": end_date,
        "transactions_count": int(len(expenses)),
        "total_spent": round(float(expenses["expense_amount"].sum()), 2),
        "average_transaction": round(float(expenses["expense_amount"].mean()), 2)
        if len(expenses) > 0
        else 0,
        "top_merchants": merchants,
    }


def top_categories(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Топ категорій витрат за період.
    Закриває сценарій: 'Топ-5 категорій витрат за червень'.
    """
    df = load_transactions()
    period_df = filter_period(df, start_date, end_date)
    expenses = period_df[period_df["is_expense"]]

    grouped = (
        expenses.groupby("category")
        .agg(
            total_spent=("expense_amount", "sum"),
            transactions_count=("expense_amount", "count"),
        )
        .reset_index()
        .sort_values("total_spent", ascending=False)
        .head(limit)
    )

    grouped["total_spent"] = grouped["total_spent"].round(2)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "limit": limit,
        "categories": grouped.to_dict(orient="records"),
    }


def last_payment(merchant: str) -> dict[str, Any]:
    """
    Шукає останній платіж по merchant.
    Закриває сценарій: 'Дата останнього платежу за Netflix?'
    """
    df = load_transactions()
    value = merchant.strip().lower()

    matches = df[
        df["merchant"].str.lower().str.contains(value, na=False)
    ].sort_values("date", ascending=False)

    if matches.empty:
        return {
            "merchant_query": merchant,
            "found": False,
            "message": "No matching transactions found",
        }

    row = matches.iloc[0]

    return {
        "merchant_query": merchant,
        "found": True,
        "last_payment_date": row["date"].strftime("%Y-%m-%d %H:%M:%S"),
        "merchant": row["merchant"],
        "amount": round(float(row["amount"]), 2),
        "category": row["category"],
        "account": row["account"],
    }


def subscriptions_summary() -> dict[str, Any]:
    """
    Аналіз підписок.
    Важливо для патерну Forgotten subscription.
    """
    df = load_transactions()

    subs = df[
        (df["is_expense"])
        & (df["category"] == "subscriptions")
    ].copy()

    if subs.empty:
        return {
            "subscriptions": [],
            "message": "No subscriptions found",
        }

    grouped = (
        subs.groupby("merchant")
        .agg(
            total_spent=("expense_amount", "sum"),
            transactions_count=("expense_amount", "count"),
            first_payment=("date", "min"),
            last_payment=("date", "max"),
            avg_payment=("expense_amount", "mean"),
        )
        .reset_index()
        .sort_values("total_spent", ascending=False)
    )

    grouped["total_spent"] = grouped["total_spent"].round(2)
    grouped["avg_payment"] = grouped["avg_payment"].round(2)
    grouped["first_payment"] = grouped["first_payment"].dt.strftime("%Y-%m-%d")
    grouped["last_payment"] = grouped["last_payment"].dt.strftime("%Y-%m-%d")

    max_date = df["date"].max()

    grouped["days_since_last_payment"] = grouped["last_payment"].apply(
        lambda x: int((max_date - pd.to_datetime(x)).days)
    )

    forgotten = grouped[grouped["days_since_last_payment"] >= 90]

    return {
        "subscriptions": grouped.to_dict(orient="records"),
        "possible_forgotten_subscriptions": forgotten.to_dict(orient="records"),
    }


def late_night_delivery_stats(hour_from: int = 21) -> dict[str, Any]:
    """
    Аналіз доставки після 21:00.
    Важливо для патерну Late-night delivery.
    """
    df = load_transactions()

    delivery = df[
        (df["is_expense"])
        & (df["category"] == "delivery")
    ].copy()

    late = delivery[delivery["hour"] >= hour_from]

    total_count = len(delivery)
    late_count = len(late)

    return {
        "category": "delivery",
        "hour_from": hour_from,
        "delivery_transactions_count": int(total_count),
        "late_night_transactions_count": int(late_count),
        "late_night_share_pct": round((late_count / total_count) * 100, 2)
        if total_count
        else 0,
        "delivery_total_spent": round(float(delivery["expense_amount"].sum()), 2),
        "late_night_total_spent": round(float(late["expense_amount"].sum()), 2),
        "top_late_night_merchants": (
            late.groupby("merchant")["expense_amount"]
            .sum()
            .sort_values(ascending=False)
            .round(2)
            .to_dict()
        ),
    }


def weekend_vs_weekday_stats() -> dict[str, Any]:
    """
    Порівнює витрати у вихідні та будні.
    Важливо для патерну Weekend spike.
    """
    df = load_transactions()
    expenses = df[df["is_expense"]].copy()

    weekend = expenses[expenses["is_weekend"]]
    weekday = expenses[~expenses["is_weekend"]]

    weekend_avg = weekend["expense_amount"].mean()
    weekday_avg = weekday["expense_amount"].mean()

    spike_pct = (
        ((weekend_avg - weekday_avg) / weekday_avg) * 100
        if weekday_avg and not pd.isna(weekday_avg)
        else 0
    )

    return {
        "weekday_transactions_count": int(len(weekday)),
        "weekend_transactions_count": int(len(weekend)),
        "weekday_avg_transaction": round(float(weekday_avg), 2),
        "weekend_avg_transaction": round(float(weekend_avg), 2),
        "weekend_spike_pct": round(float(spike_pct), 2),
        "weekday_total_spent": round(float(weekday["expense_amount"].sum()), 2),
        "weekend_total_spent": round(float(weekend["expense_amount"].sum()), 2),
    }


def monthly_category_spending(category: str) -> dict[str, Any]:
    """
    Витрати по категорії в розрізі місяців.
    Важливо для кави, доставки, підписок.
    """
    df = load_transactions()
    normalized_category = normalize_category(category)

    expenses = df[
        (df["is_expense"])
        & (df["category"] == normalized_category)
    ]

    grouped = (
        expenses.groupby("month")
        .agg(
            total_spent=("expense_amount", "sum"),
            transactions_count=("expense_amount", "count"),
        )
        .reset_index()
        .sort_values("month")
    )

    grouped["total_spent"] = grouped["total_spent"].round(2)

    return {
        "category": normalized_category,
        "months": grouped.to_dict(orient="records"),
    }


def credit_card_behavior() -> dict[str, Any]:
    """
    Аналіз поведінки по кредитній картці.
    Важливо для сценарію: 'Як швидше виплатити кредитну картку?'
    """
    df = load_transactions()

    credit_rows = df[df["account"] == "credit_card"].copy()
    payments = df[df["category"] == "credit_payment"].copy()

    monthly_payments = (
        payments.groupby("month")
        .agg(
            payment_total=("expense_amount", "sum"),
            payments_count=("expense_amount", "count"),
        )
        .reset_index()
        .sort_values("month")
    )

    monthly_payments["payment_total"] = monthly_payments["payment_total"].round(2)

    minimum_like = monthly_payments[
        monthly_payments["payment_total"].between(45, 60)
    ]

    return {
        "credit_card_transactions_count": int(len(credit_rows)),
        "credit_card_total_spent": round(float(credit_rows["expense_amount"].sum()), 2),
        "monthly_payments": monthly_payments.to_dict(orient="records"),
        "minimum_like_payment_months": int(len(minimum_like)),
    }


def suspicious_transactions() -> dict[str, Any]:
    """
    Пошук підозрілих транзакцій.
    Важливо: агент не повинен сам 'вирішувати fraud',
    а має ескалювати користувача до підтримки.
    """
    df = load_transactions()

    suspicious_merchants = ["booking.com", "aliexpress"]

    mask = (
        (df["account"] == "credit_card")
        & (
            df["merchant"]
            .str.lower()
            .apply(lambda x: any(m in x for m in suspicious_merchants))
        )
    )

    rows = df[mask].sort_values("date", ascending=False)

    return {
        "suspicious_transactions_count": int(len(rows)),
        "transactions": to_records(rows, limit=10),
        "recommended_action": (
            "Escalate to support. Agent must not resolve fraud or chargeback directly."
        ),
    }


def simulate_category_reduction(
    category: str,
    reduction_pct: float,
    months: int = 12,
) -> dict[str, Any]:
    """
    Симуляція економії.
    Приклад: доставка -50% за рік.
    """
    df = load_transactions()
    normalized_category = normalize_category(category)

    expenses = df[
        (df["is_expense"])
        & (df["category"] == normalized_category)
    ]

    monthly = (
        expenses.groupby("month")["expense_amount"]
        .sum()
        .reset_index()
        .sort_values("month")
    )

    avg_monthly = monthly["expense_amount"].mean() if not monthly.empty else 0
    estimated_saving_per_month = avg_monthly * reduction_pct
    estimated_saving_total = estimated_saving_per_month * months

    return {
        "category": normalized_category,
        "reduction_pct": reduction_pct,
        "avg_monthly_spending": round(float(avg_monthly), 2),
        "estimated_saving_per_month": round(float(estimated_saving_per_month), 2),
        "months": months,
        "estimated_saving_total": round(float(estimated_saving_total), 2),
    }


def savings_opportunities(target_amount: float = 200) -> dict[str, Any]:
    """
    Пропонує потенційні місця економії на основі реальних патернів у даних.
    Це ще не фінальна відповідь агента, а сирі факти для нього.
    """
    delivery_half = simulate_category_reduction("delivery", 0.5, months=1)
    coffee_cut = simulate_category_reduction("coffee", 0.35, months=1)
    subs = subscriptions_summary()

    opportunities = []

    if delivery_half["estimated_saving_per_month"] > 0:
        opportunities.append(
            {
                "area": "delivery",
                "reason": "Reduce delivery spending by 50%",
                "estimated_monthly_saving": delivery_half["estimated_saving_per_month"],
            }
        )

    if coffee_cut["estimated_saving_per_month"] > 0:
        opportunities.append(
            {
                "area": "coffee",
                "reason": "Replace part of weekday coffee purchases with home coffee",
                "estimated_monthly_saving": coffee_cut["estimated_saving_per_month"],
            }
        )

    for item in subs.get("possible_forgotten_subscriptions", []):
        opportunities.append(
            {
                "area": "subscriptions",
                "reason": f"Possible forgotten subscription: {item['merchant']}",
                "estimated_monthly_saving": item["avg_payment"],
            }
        )

    total = sum(x["estimated_monthly_saving"] for x in opportunities)

    return {
        "target_amount": target_amount,
        "estimated_total_saving": round(float(total), 2),
        "target_reached": total >= target_amount,
        "opportunities": opportunities,
    }


if __name__ == "__main__":
    print("Dataset summary:")
    print(dataset_summary())

    print("\nTop categories:")
    print(top_categories(limit=5))

    print("\nCoffee monthly spending:")
    print(monthly_category_spending("coffee"))

    print("\nLate-night delivery:")
    print(late_night_delivery_stats())

    print("\nSubscriptions:")
    print(subscriptions_summary())

    print("\nSuspicious transactions:")
    print(suspicious_transactions())