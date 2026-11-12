"""Shared service shell for the 入职台账 / 离职台账 ledgers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.hr.ledger_repository import LedgerRecordRepository
from app.shared.base_model import BaseModel


class LedgerRecordService[ModelT: BaseModel]:
    repository: type[LedgerRecordRepository[ModelT]]
    not_found_label: str

    def __init__(self, session: AsyncSession) -> None:
        self.repo = self.repository(session)

    async def get_record(self, record_id: UUID) -> ModelT:
        record = await self.repo.get_by_id(record_id)
        if not record:
            raise NotFoundException(self.not_found_label, str(record_id))
        return record

    async def list_records(
        self,
        *,
        keyword: str | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ModelT], int]:
        return await self.repo.list_records(
            keyword=keyword,
            department=department,
            page=page,
            page_size=page_size,
        )

    async def create_record(self, payload: Any) -> ModelT:
        record = self.repo.model(**payload.model_dump())
        return await self.repo.create(record)

    async def update_record(self, record_id: UUID, payload: Any) -> ModelT:
        record = await self.get_record(record_id)
        changes = {field: value for field, value in payload.model_dump(exclude_unset=True).items() if value is not None}
        self._validate_update(record, changes)
        for field, value in changes.items():
            setattr(record, field, value)
        self._after_update(record)
        return await self.repo.update(record)

    async def delete_record(self, record_id: UUID) -> None:
        record = await self.get_record(record_id)
        await self.repo.soft_delete(record)

    def _validate_update(self, record: ModelT, changes: dict[str, Any]) -> None:
        """Hook for subclasses that need cross-field validation."""

    def _after_update(self, record: ModelT) -> None:
        """Hook for subclasses that derive values from the updated fields."""
