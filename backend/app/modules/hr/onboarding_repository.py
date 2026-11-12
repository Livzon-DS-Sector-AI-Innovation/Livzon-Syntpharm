"""SQLAlchemy adapter for the 2026 入职台账 (ticket #199)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import OnboardingRecord


class OnboardingRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, record_id: UUID) -> OnboardingRecord | None:
        result = await self.session.execute(
            select(OnboardingRecord).where(
                OnboardingRecord.id == record_id,
                OnboardingRecord.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_records(
        self,
        *,
        keyword: str | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OnboardingRecord], int]:
        stmt = select(OnboardingRecord).where(OnboardingRecord.is_deleted.is_(False))

        if keyword:
            pattern = f"%{keyword.strip()}%"
            stmt = stmt.where(
                or_(
                    OnboardingRecord.serial_no.ilike(pattern),
                    OnboardingRecord.name.ilike(pattern),
                    OnboardingRecord.department_level1.ilike(pattern),
                    OnboardingRecord.department_level2.ilike(pattern),
                    OnboardingRecord.position.ilike(pattern),
                )
            )
        if department:
            pattern = f"%{department.strip()}%"
            stmt = stmt.where(
                or_(
                    OnboardingRecord.department_level1.ilike(pattern),
                    OnboardingRecord.department_level2.ilike(pattern),
                )
            )

        total_result = await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar() or 0

        data_stmt = (
            stmt.order_by(OnboardingRecord.hire_date.desc(), OnboardingRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        data_result = await self.session.execute(data_stmt)
        return list(data_result.scalars().all()), total

    async def create(self, record: OnboardingRecord) -> OnboardingRecord:
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def update(self, record: OnboardingRecord) -> OnboardingRecord:
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def soft_delete(self, record: OnboardingRecord) -> None:
        record.is_deleted = True
        await self.session.flush()
