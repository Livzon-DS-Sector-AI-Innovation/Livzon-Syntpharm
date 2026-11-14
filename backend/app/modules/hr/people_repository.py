"""SQLAlchemy adapter for the personnel mirror (ticket #198).

Implements the :class:`app.modules.hr.people_sync.EmployeeProfileStore` port over
``hr.employee_profiles`` and reads the platform directory (``identity.users`` /
``identity.departments``) to decide which people are in scope. Never deletes:
the nightly sync only enriches known people.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.hr.models import EmployeeProfile, HrDepartment
from app.modules.hr.org_domain import OrgScopes
from app.modules.hr.org_settings import load_org_scopes
from app.modules.hr.people_domain import EmployeeProfileRecord

_STAFF_STATUS_BY_LABEL: dict[str, int] = {
    "在职": 1,
    "离职": 2,
    "待入职": 3,
    "取消入职": 4,
}


def parse_staff_status(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    text = value.strip()
    if text in _STAFF_STATUS_BY_LABEL:
        return _STAFF_STATUS_BY_LABEL[text]
    try:
        return int(text)
    except ValueError:
        return None


async def _list_department_rows(session: AsyncSession) -> list[HrDepartment]:
    result = await session.execute(
        select(HrDepartment).where(
            HrDepartment.is_deleted.is_(False),
            HrDepartment.status_is_deleted.is_(False),
        )
    )
    return list(result.scalars().all())


async def in_scope_department_ids(session: AsyncSession, scopes: OrgScopes | None = None) -> set[str]:
    """Return every department id under any configured company root."""
    org_scopes = scopes if scopes is not None else await load_org_scopes(session)
    departments = await _list_department_rows(session)
    scoped: set[str] = set()
    for department in departments:
        department_id = department.feishu_department_id
        if not department_id:
            continue
        if org_scopes.is_root(department_id):
            scoped.add(department_id)
        elif org_scopes.is_direct_child(department.parent_feishu_department_id):
            scoped.add(department_id)
        elif org_scopes.covers_path(department.department_path):
            scoped.add(department_id)

    # Close over missing/incomplete paths so deep departments are never lost.
    changed = True
    while changed:
        changed = False
        for department in departments:
            department_id = department.feishu_department_id
            if not department_id or department_id in scoped:
                continue
            if department.parent_feishu_department_id in scoped:
                scoped.add(department_id)
                changed = True
    return scoped


async def resolve_filter_department_ids(session: AsyncSession, selected: str | None) -> set[str] | None:
    """Expand a tree selection to the department ids its people may belong to.

    ``None`` means "no department filter" (all companies). Any selected node
    (company root or deeper) matches itself plus all descendants at any depth.
    """
    if not selected:
        return None
    org_scopes = await load_org_scopes(session)
    scope = await in_scope_department_ids(session, org_scopes)
    if selected not in scope:
        return set()
    departments = await _list_department_rows(session)
    selected_ids = {selected}
    changed = True
    while changed:
        changed = False
        for department in departments:
            department_id = department.feishu_department_id
            if not department_id or department_id in selected_ids or department_id not in scope:
                continue
            in_selected_path = bool(
                department.department_path
                and any(
                    isinstance(entry, dict) and str(entry.get("id")) == selected for entry in department.department_path
                )
            )
            if department.parent_feishu_department_id in selected_ids or in_selected_path:
                selected_ids.add(department_id)
                changed = True
    return selected_ids


async def _resolve_department_fields(
    session: AsyncSession,
    department_ids: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    ids = [department_id for department_id in department_ids if department_id]
    if not ids:
        return [], []
    result = await session.execute(
        select(HrDepartment).where(HrDepartment.feishu_department_id.in_(ids), HrDepartment.is_deleted.is_(False))
    )
    rows = {row.feishu_department_id: row for row in result.scalars().all()}
    names = [rows[department_id].name if department_id in rows else "" for department_id in ids]
    paths: list[list[dict[str, Any]]] = []
    for department_id in ids:
        row = rows.get(department_id)
        path_value = row.department_path if row is not None else None
        if path_value:
            paths.append(path_value)
    best = max(paths, key=len) if paths else []
    path = [{"id": str(entry.get("id", "")), "name": str(entry.get("name", ""))} for entry in best]
    return names, path


class SqlAlchemyEmployeeProfileStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_scope_department_ids(self) -> list[str]:
        return sorted(await in_scope_department_ids(self.session))

    async def upsert_profile(
        self,
        record: EmployeeProfileRecord,
        *,
        department_ids: list[str],
    ) -> bool:
        result = await self.session.execute(select(EmployeeProfile).where(EmployeeProfile.open_id == record.open_id))
        profile = result.scalar_one_or_none()
        created = profile is None
        if profile is None:
            profile = EmployeeProfile(open_id=record.open_id)
            self.session.add(profile)

        department_names, department_path = await _resolve_department_fields(self.session, department_ids)

        profile.name = record.name
        profile.mobile = record.mobile
        profile.email = record.email
        profile.enterprise_email = record.enterprise_email
        profile.email_aliases = list(record.email_aliases)
        profile.gender = record.gender
        # 学历/年龄不在员工目录 mget 的必取字段内；只有源数据提供时才覆盖，
        # 避免每次同步清空离职台账需要的人员快照来源。
        if record.education:
            profile.education = record.education
        if record.age is not None:
            profile.age = record.age
        profile.description = record.description
        profile.avatar_72 = record.avatar_72
        profile.avatar_240 = record.avatar_240
        profile.avatar_640 = record.avatar_640
        profile.avatar_origin = record.avatar_origin
        profile.background_image = record.background_image
        profile.geo_name = record.geo_name
        profile.active_status = record.active_status
        profile.is_resigned = record.is_resigned
        profile.resign_time = record.resign_time
        profile.is_admin = record.is_admin
        profile.is_primary_admin = record.is_primary_admin
        profile.data_source = record.data_source
        profile.employee_no = record.employee_no
        profile.job_title_id = record.job_title_id
        profile.job_title_name = record.job_title_name
        profile.hire_date = record.hire_date
        profile.employment_type = record.employment_type
        profile.staff_status = record.staff_status
        profile.work_country_or_region = record.work_country_or_region
        profile.work_place_id = record.work_place_id
        profile.work_place_name = record.work_place_name
        profile.work_station = record.work_station
        profile.extension_number = record.extension_number
        profile.dotted_line_leader_ids = list(record.dotted_line_leader_ids)
        profile.resign_date = record.resign_date
        profile.resign_type = record.resign_type
        profile.resign_reason = record.resign_reason
        profile.resign_remark = record.resign_remark
        profile.positions = list(record.positions)
        profile.job_level_id = record.job_level_id
        profile.job_level_name = record.job_level_name
        profile.job_family_id = record.job_family_id
        profile.job_family_name = record.job_family_name
        profile.department_ids = list(department_ids)
        profile.department_names = department_names
        profile.department_path = department_path
        profile.last_synced_at = record.last_synced_at
        await self.session.flush()
        return created

    async def list_profiles(
        self,
        *,
        department_ids: set[str] | None,
        status: int | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[EmployeeProfile], int]:
        conditions: list[ColumnElement[bool]] = [EmployeeProfile.is_deleted.is_(False)]
        if department_ids is not None:
            if not department_ids:
                return [], 0
            conditions.append(
                or_(
                    *[
                        EmployeeProfile.department_ids.contains([department_id])
                        for department_id in sorted(department_ids)
                    ]
                )
            )
        if status is not None:
            conditions.append(EmployeeProfile.staff_status == status)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    EmployeeProfile.name.ilike(pattern),
                    EmployeeProfile.employee_no.ilike(pattern),
                    EmployeeProfile.job_title_name.ilike(pattern),
                    cast(EmployeeProfile.department_names, Text).ilike(pattern),
                )
            )

        total = (
            await self.session.execute(select(func.count()).select_from(EmployeeProfile).where(*conditions))
        ).scalar_one()
        result = await self.session.execute(
            select(EmployeeProfile)
            .where(*conditions)
            .order_by(EmployeeProfile.name.asc(), EmployeeProfile.open_id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), int(total)

    async def get_profile(self, identifier: str) -> EmployeeProfile | None:
        profile: EmployeeProfile | None = None
        try:
            profile_id = uuid.UUID(identifier)
        except ValueError:
            profile_id = None
        if profile_id is not None:
            profile = (
                await self.session.execute(
                    select(EmployeeProfile).where(
                        EmployeeProfile.id == profile_id,
                        EmployeeProfile.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
        if profile is None:
            profile = (
                await self.session.execute(
                    select(EmployeeProfile).where(
                        EmployeeProfile.open_id == identifier,
                        EmployeeProfile.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
        return profile

    async def get_latest_synced_at(self) -> datetime | None:
        result = await self.session.execute(
            select(func.max(EmployeeProfile.last_synced_at)).where(EmployeeProfile.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()
