"""SQLAlchemy adapter for the department mirror (ticket #197).

Implements the :class:`app.modules.hr.org_sync.OrgDepartmentStore` port over
``hr.departments`` and ``hr.org_sync_runs``. Never hard-deletes: removed
departments are flagged via ``status_is_deleted``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import EmployeeProfile, HrDepartment, HrOrgSyncRun
from app.modules.hr.org_domain import OrgDepartmentRecord
from app.modules.hr.org_sync import SyncRunRecord


class SqlAlchemyOrgDepartmentStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_departments(self) -> list[OrgDepartmentRecord]:
        result = await self.session.execute(
            select(HrDepartment)
            .where(HrDepartment.is_deleted.is_(False))
            .order_by(HrDepartment.order, HrDepartment.name)
        )
        return [self._to_record(row) for row in result.scalars().all()]

    async def upsert_department(self, record: OrgDepartmentRecord) -> bool:
        if not record.id:
            return False
        result = await self.session.execute(select(HrDepartment).where(HrDepartment.feishu_department_id == record.id))
        department = result.scalar_one_or_none()
        created = department is None
        if department is None:
            department = HrDepartment(feishu_department_id=record.id)
            self.session.add(department)

        department.name = record.name
        department.level = max(len(record.department_path) - 1, 0) if record.department_path else None
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
        result = await self.session.execute(
            select(HrDepartment).where(HrDepartment.feishu_department_id == department_id)
        )
        department = result.scalar_one_or_none()
        if department is not None:
            department.status_is_deleted = True
            await self.session.flush()

    async def record_sync_run(self, run: SyncRunRecord, *, run_id: UUID | None = None) -> None:
        row = await self.session.get(HrOrgSyncRun, run_id) if run_id is not None else None
        if row is None:
            row = HrOrgSyncRun(id=run_id) if run_id is not None else HrOrgSyncRun()
            self.session.add(row)
        row.status = run.status
        row.department_count = run.department_count
        row.people_count = run.people_count
        row.error_message = run.error_message
        row.started_at = run.started_at
        row.finished_at = run.finished_at
        await self.session.flush()

    async def rollback(self) -> None:
        await self.session.rollback()

    @staticmethod
    def _to_record(row: HrDepartment) -> OrgDepartmentRecord:
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
        select(EmployeeProfile).where(
            EmployeeProfile.is_deleted.is_(False),
            EmployeeProfile.open_id.in_(ids),
        )
    )
    names: dict[str, str] = {}
    for profile in result.scalars().all():
        if profile.open_id in ids and profile.name:
            names.setdefault(profile.open_id, profile.name)
    return names


async def resolve_leader_avatars(session: AsyncSession, leader_ids: set[str]) -> dict[str, str]:
    """Map Feishu leader ids to profile avatar URLs; unresolved ids are absent."""
    ids = {leader_id for leader_id in leader_ids if leader_id}
    if not ids:
        return {}
    result = await session.execute(
        select(EmployeeProfile).where(
            EmployeeProfile.is_deleted.is_(False),
            EmployeeProfile.open_id.in_(ids),
        )
    )
    avatars: dict[str, str] = {}
    for profile in result.scalars().all():
        if profile.open_id not in ids:
            continue
        avatar = profile.avatar_72 or profile.avatar_240 or profile.avatar_640 or profile.avatar_origin
        if avatar:
            avatars.setdefault(profile.open_id, avatar)
    return avatars


async def get_latest_sync_run(session: AsyncSession) -> HrOrgSyncRun | None:
    result = await session.execute(
        select(HrOrgSyncRun)
        .where(HrOrgSyncRun.is_deleted.is_(False))
        .order_by(HrOrgSyncRun.started_at.desc(), HrOrgSyncRun.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
