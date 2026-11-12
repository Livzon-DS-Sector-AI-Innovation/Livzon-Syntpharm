"""SQLAlchemy adapter for the 2026 离职台账 (ticket #200)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import DepartureRecord, EmployeeProfile


class DepartureRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, record_id: UUID) -> DepartureRecord | None:
        result = await self.session.execute(
            select(DepartureRecord).where(
                DepartureRecord.id == record_id,
                DepartureRecord.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_profile(self, person_id: UUID) -> EmployeeProfile | None:
        result = await self.session.execute(
            select(EmployeeProfile).where(
                EmployeeProfile.id == person_id,
                EmployeeProfile.is_deleted.is_(False),
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
    ) -> tuple[list[DepartureRecord], int]:
        stmt = select(DepartureRecord).where(DepartureRecord.is_deleted.is_(False))

        if keyword:
            pattern = f"%{keyword.strip()}%"
            stmt = stmt.where(
                or_(
                    DepartureRecord.name.ilike(pattern),
                    DepartureRecord.department_level1.ilike(pattern),
                    DepartureRecord.department_level2.ilike(pattern),
                    DepartureRecord.position.ilike(pattern),
                )
            )
        if department:
            pattern = f"%{department.strip()}%"
            stmt = stmt.where(
                or_(
                    DepartureRecord.department_level1.ilike(pattern),
                    DepartureRecord.department_level2.ilike(pattern),
                )
            )

        total_result = await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar() or 0

        data_stmt = (
            stmt.order_by(DepartureRecord.leave_date.desc(), DepartureRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        data_result = await self.session.execute(data_stmt)
        return list(data_result.scalars().all()), total

    async def create(self, record: DepartureRecord) -> DepartureRecord:
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def update(self, record: DepartureRecord) -> DepartureRecord:
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def soft_delete(self, record: DepartureRecord) -> None:
        record.is_deleted = True
        await self.session.flush()
