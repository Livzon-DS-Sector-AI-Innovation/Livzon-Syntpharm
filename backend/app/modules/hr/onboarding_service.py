"""Service for the 2026 入职台账 (ticket #199).

The ledger is manual: every field is entered by hand, nothing is resolved
from Feishu, and deletes are soft so mistakes stay auditable.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.hr.models import OnboardingRecord
from app.modules.hr.onboarding_repository import OnboardingRecordRepository
from app.modules.hr.onboarding_schemas import OnboardingRecordCreate, OnboardingRecordUpdate


class OnboardingRecordService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = OnboardingRecordRepository(session)

    async def get_record(self, record_id: UUID) -> OnboardingRecord:
        record = await self.repo.get_by_id(record_id)
        if not record:
            raise NotFoundException("入职记录", str(record_id))
        return record

    async def list_records(
        self,
        *,
        keyword: str | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OnboardingRecord], int]:
        return await self.repo.list_records(
            keyword=keyword,
            department=department,
            page=page,
            page_size=page_size,
        )

    async def create_record(self, payload: OnboardingRecordCreate) -> OnboardingRecord:
        record = OnboardingRecord(**payload.model_dump())
        return await self.repo.create(record)

    async def update_record(self, record_id: UUID, payload: OnboardingRecordUpdate) -> OnboardingRecord:
        record = await self.get_record(record_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(record, field, value)
        return await self.repo.update(record)

    async def delete_record(self, record_id: UUID) -> None:
        record = await self.get_record(record_id)
        await self.repo.soft_delete(record)
