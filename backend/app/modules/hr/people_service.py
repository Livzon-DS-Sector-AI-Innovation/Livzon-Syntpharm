"""Read model for the 员工档案 personnel browser (ticket #198)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.hr.models import EmployeeProfile
from app.modules.hr.people_domain import (
    active_status_label,
    data_source_label,
    department_levels_from,
    gender_label,
    staff_status_label,
)
from app.modules.hr.people_repository import (
    SqlAlchemyEmployeeProfileStore,
    parse_staff_status,
    resolve_filter_department_ids,
)


def _avatar_url(profile: EmployeeProfile) -> str:
    return profile.avatar_240 or profile.avatar_72 or profile.avatar_origin or ""


def _levels(profile: EmployeeProfile) -> tuple[str, str]:
    return department_levels_from(profile.department_path, profile.department_names)


def list_item(profile: EmployeeProfile) -> dict[str, Any]:
    level1, level2 = _levels(profile)
    return {
        "id": str(profile.id),
        "open_id": profile.open_id,
        "name": profile.name,
        "avatar_url": _avatar_url(profile),
        "department_ids": list(profile.department_ids or []),
        "department_names": list(profile.department_names or []),
        "department_path": list(profile.department_path or []),
        "department_level1_name": level1,
        "department_level2_name": level2,
        "job_title_name": profile.job_title_name,
        "staff_status": profile.staff_status,
        "staff_status_label": staff_status_label(profile.staff_status),
        "is_resigned": profile.is_resigned,
        "last_synced_at": profile.last_synced_at,
    }


def detail(profile: EmployeeProfile) -> dict[str, Any]:
    level1, level2 = _levels(profile)
    return {
        "id": str(profile.id),
        "open_id": profile.open_id,
        "name": profile.name,
        "mobile": profile.mobile,
        "email": profile.email,
        "enterprise_email": profile.enterprise_email,
        "email_aliases": list(profile.email_aliases or []),
        "gender": profile.gender,
        "gender_label": gender_label(profile.gender),
        "education": profile.education,
        "age": profile.age,
        "description": profile.description,
        "avatar_72": profile.avatar_72,
        "avatar_240": profile.avatar_240,
        "avatar_640": profile.avatar_640,
        "avatar_origin": profile.avatar_origin,
        "avatar_url": _avatar_url(profile),
        "background_image": profile.background_image,
        "geo_name": profile.geo_name,
        "active_status": profile.active_status,
        "active_status_label": active_status_label(profile.active_status),
        "is_resigned": profile.is_resigned,
        "resign_time": profile.resign_time,
        "is_admin": profile.is_admin,
        "is_primary_admin": profile.is_primary_admin,
        "data_source": profile.data_source,
        "data_source_label": data_source_label(profile.data_source),
        "employee_no": profile.employee_no,
        "job_title_id": profile.job_title_id,
        "job_title_name": profile.job_title_name,
        "hire_date": profile.hire_date,
        "employment_type": profile.employment_type,
        "staff_status": profile.staff_status,
        "staff_status_label": staff_status_label(profile.staff_status),
        "work_country_or_region": profile.work_country_or_region,
        "work_place_id": profile.work_place_id,
        "work_place_name": profile.work_place_name,
        "work_station": profile.work_station,
        "extension_number": profile.extension_number,
        "dotted_line_leader_ids": list(profile.dotted_line_leader_ids or []),
        "resign_date": profile.resign_date,
        "resign_type": profile.resign_type,
        "resign_reason": profile.resign_reason,
        "resign_remark": profile.resign_remark,
        "positions": list(profile.positions or []),
        "job_level_id": profile.job_level_id,
        "job_level_name": profile.job_level_name,
        "job_family_id": profile.job_family_id,
        "job_family_name": profile.job_family_name,
        "department_ids": list(profile.department_ids or []),
        "department_names": list(profile.department_names or []),
        "department_path": list(profile.department_path or []),
        "department_level1_name": level1,
        "department_level2_name": level2,
        "last_synced_at": profile.last_synced_at,
    }


async def list_people(
    session: AsyncSession,
    *,
    department_id: str | None,
    status: str | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int, Any]:
    store = SqlAlchemyEmployeeProfileStore(session)
    department_ids = await resolve_filter_department_ids(session, department_id)
    profiles, total = await store.list_profiles(
        department_ids=department_ids,
        status=parse_staff_status(status),
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return [list_item(profile) for profile in profiles], total, await store.get_latest_synced_at()


async def get_person(session: AsyncSession, identifier: str) -> dict[str, Any]:
    store = SqlAlchemyEmployeeProfileStore(session)
    profile = await store.get_profile(identifier)
    if profile is None:
        raise AppException(status_code=404, message="员工不存在")
    return detail(profile)
