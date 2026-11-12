"""SQLAlchemy adapter for the department mirror (ticket #197).

Implements the :class:`app.modules.hr.org_sync.OrgDepartmentStore` port over
``identity.departments`` and ``identity.org_sync_runs``. Never hard-deletes:
removed departments are flagged via ``status_is_deleted``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.org_domain import OrgDepartmentRecord
from app.platform.identity.models import Department, OrgSyncRun, User


class SqlAlchemyOrgDepartmentStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_departments(self) -> list[OrgDepartmentRecord]:
        result = await self.session.execute(
            select(Department).where(Department.is_deleted.is_(False)).order_by(Department.order, Department.name)
        )
        return [self._to_record(row) for row in result.scalars().all()]

    async def upsert_department(self, record: OrgDepartmentRecord) -> bool:
        if not record.id:
            return False
        result = await self.session.execute(select(Department).where(Department.feishu_department_id == record.id))
        department = result.scalar_one_or_none()
        created = department is None
        if department is None:
            department = Department(feishu_department_id=record.id)
            self.session.add(department)

        department.name = record.name
        department.parent_feishu_department_id = record.parent_id
        department.order = record.order
        department.order_weight = record.order_weight
        department.department_path = record.department_path or None
        department.leader_ids = record.leader_ids or None
        department.recursive_members_count = record.recursive_members_count
        department.direct_members_count = record.direct_members_count
        department.recursive_departments_count = record.recursive_departments_count
        department.direct_departments_count = record.direct_departments_count
        department.data_source = record.data_source
        department.custom_fields = record.custom_fields or None
        department.enabled_status = record.enabled_status
        department.status_is_deleted = record.hidden
        department.directory_synced_at = datetime.now(UTC)
        await self.session.flush()
        return created

    async def hide_department(self, department_id: str) -> None:
        result = await self.session.execute(select(Department).where(Department.feishu_department_id == department_id))
        department = result.scalar_one_or_none()
        if department is not None:
            department.status_is_deleted = True
            await self.session.flush()

    async def record_sync_run(self, **kwargs: Any) -> None:
        self.session.add(
            OrgSyncRun(
                status=kwargs["status"],
                department_count=kwargs["department_count"],
                people_count=kwargs["people_count"],
                error_message=kwargs["error_message"],
                started_at=kwargs["started_at"],
                finished_at=kwargs["finished_at"],
            )
        )
        await self.session.flush()

    @staticmethod
    def _to_record(row: Department) -> OrgDepartmentRecord:
        return OrgDepartmentRecord(
            id=row.feishu_department_id,
            name=row.name,
            parent_id=row.parent_feishu_department_id,
            order=row.order or 0,
            order_weight=row.order_weight,
            hidden=bool(row.status_is_deleted),
            leader_ids=list(row.leader_ids or []),
            department_path=list(row.department_path or []),
            enabled_status=row.enabled_status,
            recursive_members_count=row.recursive_members_count or 0,
            direct_members_count=row.direct_members_count or 0,
            recursive_departments_count=row.recursive_departments_count or 0,
            direct_departments_count=row.direct_departments_count or 0,
            data_source=row.data_source,
            custom_fields=list(row.custom_fields or []),
        )


async def resolve_leader_names(session: AsyncSession, leader_ids: set[str]) -> dict[str, str]:
    """Map Feishu leader ids (open_id or user_id) to employee names.

    Unresolved ids are simply absent from the map, so the API renders "—".
    """
    ids = {leader_id for leader_id in leader_ids if leader_id}
    if not ids:
        return {}
    result = await session.execute(
        select(User).where(
            User.is_deleted.is_(False),
            or_(
                User.feishu_open_id.in_(ids),
                User.feishu_user_id.in_(ids),
            ),
        )
    )
    names: dict[str, str] = {}
    for user in result.scalars().all():
        for key in (user.feishu_open_id, user.feishu_user_id):
            if key and key in ids:
                names.setdefault(key, user.name)
    return names


async def get_latest_sync_run(session: AsyncSession) -> OrgSyncRun | None:
    result = await session.execute(
        select(OrgSyncRun)
        .where(OrgSyncRun.is_deleted.is_(False))
        .order_by(OrgSyncRun.started_at.desc(), OrgSyncRun.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
