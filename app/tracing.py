from __future__ import annotations

from dotenv import load_dotenv
from langsmith import traceable


# override=True важливо:
# якщо в системі вже є старі env-змінні, .env їх перезапише.
load_dotenv(override=True)


__all__ = ["traceable"]