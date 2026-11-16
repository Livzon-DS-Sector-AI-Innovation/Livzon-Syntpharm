"""SQLAlchemy adapter for the 2026 离职台账 (ticket #200)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.modules.hr.ledger_repository import LedgerRecordRepository
from app.modules.hr.models import DepartureRecord, EmployeeProfile


class DepartureRecordRepository(LedgerRecordRepository[DepartureRecord]):
    model = DepartureRecord
    keyword_fields = ("name", "department_level1", "department_level2", "position")
    department_fields = ("department_level1", "department_level2")
    order_fields = ("leave_date",)

    async def get_profile(self, person_id: UUID) -> EmployeeProfile | None:
        result = await self.session.execute(
            select(EmployeeProfile).where(
                EmployeeProfile.id == person_id,
                EmployeeProfile.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
