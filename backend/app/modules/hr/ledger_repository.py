"""Shared query shell for the 入职台账 / 离职台账 ledgers.

Both ledgers store free-text department names, filter by keyword across a
different field set, and soft-delete. The model-specific parts (table, search
fields, ordering) live on each subclass.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.base_model import BaseModel


class LedgerRecordRepository[ModelT: BaseModel]:
    model: type[ModelT]
    keyword_fields: tuple[str, ...] = ()
    department_fields: tuple[str, ...] = ()
    order_fields: tuple[str, ...] = ()

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, record_id: UUID) -> ModelT | None:
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == record_id,
                self.model.is_deleted.is_(False),
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
    ) -> tuple[list[ModelT], int]:
        stmt = select(self.model).where(self.model.is_deleted.is_(False))

        if keyword and self.keyword_fields:
            pattern = f"%{keyword.strip()}%"
            stmt = stmt.where(or_(*(getattr(self.model, field).ilike(pattern) for field in self.keyword_fields)))
        if department and self.department_fields:
            pattern = f"%{department.strip()}%"
            stmt = stmt.where(or_(*(getattr(self.model, field).ilike(pattern) for field in self.department_fields)))

        total_result = await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar() or 0

        data_stmt = stmt.order_by(
            *(getattr(self.model, field).desc() for field in self.order_fields),
            self.model.created_at.desc(),
        )
        data_stmt = data_stmt.offset((page - 1) * page_size).limit(page_size)
        data_result = await self.session.execute(data_stmt)
        return list(data_result.scalars().all()), total

    async def create(self, record: ModelT) -> ModelT:
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def update(self, record: ModelT) -> ModelT:
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def soft_delete(self, record: ModelT) -> None:
        record.is_deleted = True
        await self.session.flush()
