"""SQLAlchemy adapter for the personnel mirror (ticket #198).

Implements the :class:`app.modules.hr.people_sync.EmployeeProfileStore` port over
``hr.employee_profiles`` and reads the platform directory (``identity.users`` /
``identity.departments``) to decide which people are in scope. Never deletes:
the nightly sync only enriches known people.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.hr.models import EmployeeProfile
from app.modules.hr.org_domain import OrgScope
from app.modules.hr.org_settings import load_org_scope
from app.modules.hr.people_domain import EmployeeProfileRecord
from app.modules.hr.people_sync import KnownPerson
from app.platform.identity.models import Department, User

_STAFF_STATUS_BY_LABEL: dict[str, int] = {
    "在职": 1,
    "离职": 2,
    "待入职": 3,
    "取消入职": 4,
}


def parse_json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if item]


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


async def in_scope_department_ids(session: AsyncSession, scope: OrgScope | None = None) -> set[str]:
    """Return the Feishu department ids that belong to the configured company."""
    org_scope = scope or await load_org_scope(session)
    result = await session.execute(select(Department).where(Department.is_deleted.is_(False)))
    departments = list(result.scalars().all())
    scoped: set[str] = set()
    for department in departments:
        if org_scope.is_direct_child(department.parent_feishu_department_id):
            scoped.add(department.feishu_department_id)
        if org_scope.covers_path(department.department_path):
            scoped.add(department.feishu_department_id)

    changed = True
    while changed:
        changed = False
        for department in departments:
            if department.feishu_department_id in scoped:
                continue
            if department.parent_feishu_department_id in scoped:
                scoped.add(department.feishu_department_id)
                changed = True
    return scoped


async def resolve_filter_department_ids(session: AsyncSession, selected: str | None) -> set[str] | None:
    """Expand a tree selection to the department ids its people may belong to.

    ``None`` means "no department filter" (company node). A selected 一级部门
    also matches its 二级部门 children; a selected 二级部门 matches itself.
    """
    org_scope = await load_org_scope(session)
    if not selected or org_scope.is_root(selected):
        return None
    scope = await in_scope_department_ids(session, org_scope)
    if selected not in scope:
        return set()
    result = await session.execute(
        select(Department.feishu_department_id).where(
            Department.is_deleted.is_(False),
            Department.parent_feishu_department_id == selected,
        )
    )
    children = {row[0] for row in result.all()} & scope
    return {selected, *children}


async def _resolve_department_fields(
    session: AsyncSession,
    department_ids: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    ids = [department_id for department_id in department_ids if department_id]
    if not ids:
        return [], []
    result = await session.execute(
        select(Department).where(Department.feishu_department_id.in_(ids), Department.is_deleted.is_(False))
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

    async def list_known_people(self) -> list[KnownPerson]:
        scope = await in_scope_department_ids(self.session)
        if not scope:
            return []

        result = await self.session.execute(
            select(User).where(User.is_deleted.is_(False), User.feishu_open_id.isnot(None))
        )
        known: dict[str, KnownPerson] = {}
        for user in result.scalars().all():
            department_ids = parse_json_list(user.feishu_department_ids)
            if not user.feishu_open_id or not set(department_ids) & scope:
                continue
            known[user.feishu_open_id] = KnownPerson(
                open_id=user.feishu_open_id,
                department_ids=department_ids,
            )

        profiles = await self.session.execute(select(EmployeeProfile).where(EmployeeProfile.is_deleted.is_(False)))
        for profile in profiles.scalars().all():
            if profile.open_id in known:
                continue
            department_ids = list(profile.department_ids or [])
            if set(department_ids) & scope:
                known[profile.open_id] = KnownPerson(open_id=profile.open_id, department_ids=department_ids)
        return list(known.values())

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
