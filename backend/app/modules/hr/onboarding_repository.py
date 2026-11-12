"""SQLAlchemy adapter for the 2026 入职台账 (ticket #199)."""

from __future__ import annotations

from app.modules.hr.ledger_repository import LedgerRecordRepository
from app.modules.hr.models import OnboardingRecord


class OnboardingRecordRepository(LedgerRecordRepository[OnboardingRecord]):
    model = OnboardingRecord
    keyword_fields = ("serial_no", "name", "department_level1", "department_level2", "position")
    department_fields = ("department_level1", "department_level2")
    order_fields = ("hire_date",)
