"""Registration project & progress log database queries."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.models.project import ProjectProgressLog, RegistrationProject


async def list_projects(
    db: AsyncSession,
    *,
    search: str | None = None,
    registration_type: str | None = None,
    status: str | None = None,
    drug_id: uuid.UUID | None = None,
) -> list[RegistrationProject]:
    """项目列表：支持名称/编号/品种模糊搜索 + 类型/状态筛选，按更新时间倒序。"""
    stmt = select(RegistrationProject).where(~RegistrationProject.is_deleted)
    if drug_id:
        stmt = stmt.where(RegistrationProject.drug_id == drug_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            RegistrationProject.name.ilike(pattern)
            | RegistrationProject.project_no.ilike(pattern)
            | RegistrationProject.product_name.ilike(pattern)
        )
    if registration_type:
        stmt = stmt.where(RegistrationProject.registration_type == registration_type)
    if status:
        stmt = stmt.where(RegistrationProject.status == status)
    stmt = stmt.order_by(RegistrationProject.updated_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_project_by_id(db: AsyncSession, project_id: uuid.UUID) -> RegistrationProject | None:
    stmt = select(RegistrationProject).where(
        RegistrationProject.id == project_id,
        ~RegistrationProject.is_deleted,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_projects_by_drug(db: AsyncSession, drug_id: uuid.UUID) -> list[RegistrationProject]:
    stmt = select(RegistrationProject).where(
        RegistrationProject.drug_id == drug_id,
        ~RegistrationProject.is_deleted,
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_project(db: AsyncSession, data: dict[str, Any]) -> RegistrationProject:
    project = RegistrationProject(**data)
    db.add(project)
    await db.flush()
    return project


async def next_project_no(db: AsyncSession, year: int) -> str:
    """生成项目编号：REG-{year}-{三位序号}，按当年已有编号最大值递增。"""
    prefix = f"REG-{year}-"
    stmt = select(func.max(RegistrationProject.project_no)).where(RegistrationProject.project_no.like(f"{prefix}%"))
    result = await db.execute(stmt)
    current_max = result.scalar_one_or_none()
    seq = int(current_max.rsplit("-", 1)[-1]) + 1 if current_max else 1
    return f"{prefix}{seq:03d}"


async def add_log(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    log_type: str,
    content: str,
    created_by: uuid.UUID | None = None,
) -> ProjectProgressLog:
    log = ProjectProgressLog(
        project_id=project_id,
        log_type=log_type,
        content=content,
        created_by=created_by,
    )
    db.add(log)
    await db.flush()
    return log


async def list_logs(db: AsyncSession, project_id: uuid.UUID) -> list[ProjectProgressLog]:
    """项目进展记录：新→旧倒序。只增不删，不提供更新/删除查询。"""
    stmt = (
        select(ProjectProgressLog)
        .where(
            ProjectProgressLog.project_id == project_id,
            ~ProjectProgressLog.is_deleted,
        )
        .order_by(ProjectProgressLog.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def latest_logs_for_projects(
    db: AsyncSession, project_ids: list[uuid.UUID]
) -> dict[uuid.UUID, ProjectProgressLog]:
    """批量取各项目最新一条进展记录（列表页「最新进展」列）。"""
    if not project_ids:
        return {}
    stmt = (
        select(ProjectProgressLog)
        .where(
            ProjectProgressLog.project_id.in_(project_ids),
            ~ProjectProgressLog.is_deleted,
        )
        .order_by(ProjectProgressLog.created_at.desc())
    )
    result = await db.execute(stmt)
    latest: dict[uuid.UUID, ProjectProgressLog] = {}
    for log in result.scalars().all():
        latest.setdefault(log.project_id, log)
    return latest


async def count_kpi(db: AsyncSession, due_before: date) -> dict[str, int]:
    """KPI 统计：申报前 / 已受理·审评中 / 临期未递交（含逾期）/ 已获批。"""
    base = select(func.count()).select_from(RegistrationProject).where(~RegistrationProject.is_deleted)

    async def _count(*conditions: Any) -> int:
        result = await db.execute(base.where(*conditions))
        return result.scalar_one()

    pre_submission = await _count(RegistrationProject.status.in_(("draft", "preparing", "submitted")))
    accepted_reviewing = await _count(RegistrationProject.status.in_(("accepted", "under_review")))
    due_soon = await _count(
        RegistrationProject.status.in_(("draft", "preparing")),
        RegistrationProject.planned_submission_date.is_not(None),
        RegistrationProject.planned_submission_date <= due_before,
    )
    approved = await _count(RegistrationProject.status == "approved")
    return {
        "pre_submission": pre_submission,
        "accepted_reviewing": accepted_reviewing,
        "due_soon": due_soon,
        "approved": approved,
    }
