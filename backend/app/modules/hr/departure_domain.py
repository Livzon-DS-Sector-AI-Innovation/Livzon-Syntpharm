"""Domain vocabulary for the 2026 离职台账 (ticket #200)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

LeaveCategory = Literal["主动离职", "被动离职", "实习生离职", "退休返聘到期"]

LEAVE_CATEGORIES: tuple[str, ...] = ("主动离职", "被动离职", "实习生离职", "退休返聘到期")

_DAYS_PER_YEAR = Decimal("365.25")


def compute_tenure_years(hire_date: date, leave_date: date) -> float:
    """司龄（年）= 入职到离职的天数 / 365.25，保留一位小数。"""
    days = (leave_date - hire_date).days
    return float((Decimal(days) / _DAYS_PER_YEAR).quantize(Decimal("0.1")))
