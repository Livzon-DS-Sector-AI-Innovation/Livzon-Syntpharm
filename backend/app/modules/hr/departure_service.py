"""Service for the 2026 离职台账 (ticket #200).

The departures ledger is manual. Selecting a person snapshots the fields the
personnel mirror owns, computes 司龄 from the dates, and never refreshes those
snapshot fields from later Feishu syncs.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.modules.hr.departure_domain import compute_tenure_years
from app.modules.hr.departure_repository import DepartureRecordRepository
from app.modules.hr.departure_schemas import DepartureRecordCreate, DepartureRecordUpdate
from app.modules.hr.models import DepartureRecord, EmployeeProfile
from app.modules.hr.people_domain import department_levels_from, gender_label

_INCOMPLETE_PROFILE = "员工档案缺少离职台账所需的人员信息"


def _position_of(profile: EmployeeProfile) -> str:
    if profile.job_title_name.strip():
        return profile.job_title_name.strip()
    for position in profile.positions or []:
        name = position.get("name") if isinstance(position, dict) else None
        if isinstance(name, str) and name.strip():
            return name.strip()
    return ""


def _snapshot(profile: EmployeeProfile) -> dict[str, Any]:
    level1, level2 = department_levels_from(profile.department_path, profile.department_names)
    gender = gender_label(profile.gender)
    position = _position_of(profile)
    education = profile.education.strip()

    if not level1 or not level2 or not position or not profile.hire_date or education == "":
        raise AppException(status_code=422, message=_INCOMPLETE_PROFILE)
    if gender not in ("男", "女") or profile.age is None:
        raise AppException(status_code=422, message=_INCOMPLETE_PROFILE)

    return {
        "department_level1": level1,
        "department_level2": level2,
        "name": profile.name,
        "gender": gender,
        "position": position,
        "hire_date": profile.hire_date,
        "education": education,
        "age": profile.age,
    }


class DepartureRecordService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = DepartureRecordRepository(session)

    async def get_record(self, record_id: UUID) -> DepartureRecord:
        record = await self.repo.get_by_id(record_id)
        if not record:
            raise NotFoundException("离职记录", str(record_id))
        return record

    async def list_records(
        self,
        *,
        keyword: str | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DepartureRecord], int]:
        return await self.repo.list_records(
            keyword=keyword,
            department=department,
            page=page,
            page_size=page_size,
        )

    async def create_record(self, payload: DepartureRecordCreate) -> DepartureRecord:
        profile = await self.repo.get_profile(payload.person_id)
        if profile is None:
            raise NotFoundException("员工档案", str(payload.person_id))

        snapshot = _snapshot(profile)
        hire_date = snapshot["hire_date"]
        if payload.leave_date < hire_date:
            raise AppException(status_code=422, message="离职日期不能早于入职日期")

        record = DepartureRecord(
            person_id=profile.id,
            **snapshot,
            position_level=payload.position_level,
            personnel_identity=payload.personnel_identity,
            leave_date=payload.leave_date,
            leave_category=payload.leave_category,
            leave_reason=payload.leave_reason,
            tenure_years=compute_tenure_years(hire_date, payload.leave_date),
            group_classification=payload.group_classification,
        )
        return await self.repo.create(record)

    async def update_record(self, record_id: UUID, payload: DepartureRecordUpdate) -> DepartureRecord:
        record = await self.get_record(record_id)
        changes = {field: value for field, value in payload.model_dump(exclude_unset=True).items() if value is not None}
        if "leave_date" in changes and changes["leave_date"] < record.hire_date:
            raise AppException(status_code=422, message="离职日期不能早于入职日期")

        for field, value in changes.items():
            setattr(record, field, value)
        record.tenure_years = compute_tenure_years(record.hire_date, record.leave_date)
        return await self.repo.update(record)

    async def delete_record(self, record_id: UUID) -> None:
        record = await self.get_record(record_id)
        await self.repo.soft_delete(record)
