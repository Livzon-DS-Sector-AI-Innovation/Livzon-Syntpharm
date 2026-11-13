"""Service for the 2026 离职台账 (ticket #200).

The departures ledger is manual. Selecting a person freezes the fields the
personnel mirror owns (部门/姓名/性别/岗位/入职日期), while 学历 and 年龄 are
prefilled from the profile and can be entered by the user because the Feishu
employee sync does not supply them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.modules.hr.departure_domain import compute_tenure_years
from app.modules.hr.departure_repository import DepartureRecordRepository
from app.modules.hr.departure_schemas import DepartureRecordCreate
from app.modules.hr.ledger_service import LedgerRecordService
from app.modules.hr.models import DepartureRecord, EmployeeProfile
from app.modules.hr.onboarding_domain import EDUCATION_LEVELS
from app.modules.hr.people_domain import department_levels_from, gender_label

_INCOMPLETE_PROFILE = "员工档案缺少离职台账所需的人员信息"


@dataclass(frozen=True)
class PersonSnapshot:
    """Frozen person fields copied from the employee profile at create time."""

    department_level1: str
    department_level2: str
    name: str
    gender: str
    position: str
    hire_date: date


def _position_of(profile: EmployeeProfile) -> str:
    if profile.job_title_name.strip():
        return profile.job_title_name.strip()
    for position in profile.positions or []:
        name = position.get("name") if isinstance(position, dict) else None
        if isinstance(name, str) and name.strip():
            return name.strip()
    return ""


def _person_snapshot(profile: EmployeeProfile) -> PersonSnapshot:
    level1, level2 = department_levels_from(profile.department_path, profile.department_names)
    gender = gender_label(profile.gender)
    position = _position_of(profile)

    if not level1 or not position or not profile.hire_date:
        raise AppException(status_code=422, message=_INCOMPLETE_PROFILE)
    if gender not in ("男", "女"):
        raise AppException(status_code=422, message=_INCOMPLETE_PROFILE)

    return PersonSnapshot(
        department_level1=level1,
        department_level2=level2,
        name=profile.name,
        gender=gender,
        position=position,
        hire_date=profile.hire_date,
    )


def _resolved_education(profile: EmployeeProfile, requested: str | None) -> str:
    value = (requested or profile.education).strip()
    return value if value in EDUCATION_LEVELS else ""


def _resolved_age(profile: EmployeeProfile, requested: int | None) -> int | None:
    return requested if requested is not None else profile.age


class DepartureRecordService(LedgerRecordService[DepartureRecord]):
    repository = DepartureRecordRepository
    not_found_label = "离职记录"
    repo: DepartureRecordRepository

    def __init__(self, session: AsyncSession) -> None:
        self.repo = DepartureRecordRepository(session)

    async def create_record(self, payload: DepartureRecordCreate) -> DepartureRecord:
        if payload.person_id is not None:
            profile = await self.repo.get_profile(payload.person_id)
            if profile is None:
                raise NotFoundException("员工档案", str(payload.person_id))
            snapshot = _person_snapshot(profile)
            person_id: UUID | None = profile.id
            education = _resolved_education(profile, payload.education)
            age = _resolved_age(profile, payload.age)
        else:
            if payload.hire_date is None or not payload.gender:
                raise AppException(status_code=422, message="手动录入时请填写入职日期和性别")
            snapshot = PersonSnapshot(
                department_level1=(payload.department_level1 or "").strip(),
                department_level2=(payload.department_level2 or "").strip(),
                name=(payload.name or "").strip(),
                gender=payload.gender,
                position=(payload.position or "").strip(),
                hire_date=payload.hire_date,
            )
            person_id = None
            education = (payload.education or "").strip()
            age = payload.age

        if payload.leave_date < snapshot.hire_date:
            raise AppException(status_code=422, message="离职日期不能早于入职日期")
        if not education or age is None:
            raise AppException(status_code=422, message="请填写学历和年龄")

        record = DepartureRecord(
            person_id=person_id,
            **asdict(snapshot),
            education=education,
            age=age,
            position_level=payload.position_level,
            personnel_identity=payload.personnel_identity,
            leave_date=payload.leave_date,
            leave_category=payload.leave_category,
            leave_reason=payload.leave_reason,
            tenure_years=compute_tenure_years(snapshot.hire_date, payload.leave_date),
            group_classification=payload.group_classification,
        )
        return await self.repo.create(record)

    def _validate_update(self, record: DepartureRecord, changes: dict[str, Any]) -> None:
        new_leave_date: date = changes.get("leave_date", record.leave_date)
        if new_leave_date < record.hire_date:
            raise AppException(status_code=422, message="离职日期不能早于入职日期")

    def _after_update(self, record: DepartureRecord) -> None:
        record.tenure_years = compute_tenure_years(record.hire_date, record.leave_date)
