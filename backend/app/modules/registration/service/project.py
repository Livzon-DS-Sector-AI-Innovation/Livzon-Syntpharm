"""Registration project service: 状态机、阶段推进、进展留痕、申报进度同步。"""

import uuid
from datetime import date, datetime, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration import repository as repo
from app.modules.registration.models.drug import Drug, DrugNode
from app.modules.registration.models.project import ProjectProgressLog, RegistrationProject
from app.modules.registration.models.review import ReviewNode
from app.modules.registration.repository import project as project_repo
from app.modules.registration.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
)
from app.modules.registration.service.prediction import predict_drug
from app.platform.identity.models import User

_TZ = ZoneInfo("Asia/Shanghai")

# ── 状态机定义 ──

#: 申报前阶段顺序（受理为界；accepted 只能由申报进度查询侧同步置达）
STAGE_ORDER = ["initiation", "data_preparation", "internal_review", "submission", "accepted"]
STAGE_LABELS = {
    "initiation": "立项",
    "data_preparation": "资料准备",
    "internal_review": "内部审核",
    "submission": "递交",
    "accepted": "已受理",
}
#: 阶段 → 状态 映射（推进阶段自动带动状态流转）
STAGE_STATUS = {
    "initiation": "draft",
    "data_preparation": "preparing",
    "internal_review": "preparing",
    "submission": "submitted",
    "accepted": "accepted",
}
STATUS_LABELS = {
    "draft": "草稿",
    "preparing": "准备中",
    "submitted": "已申报",
    "accepted": "已受理",
    "under_review": "审评中",
    "supplementary": "发补中",
    "approved": "已获批",
    "withdrawn": "已撤回",
    "terminated": "已终止",
}
#: 受理后状态（唯一维护入口为申报进度查询，本页只读）
POST_ACCEPTANCE_STATUSES = {"accepted", "under_review", "supplementary", "approved", "withdrawn", "terminated"}
#: 同步可触达的受理后状态（撤回/终止不由节点推导，同步永不覆盖）
SYNC_TARGET_STATUSES = {"accepted", "under_review", "supplementary", "approved"}
#: 最后一个审评节点序号（获批时间），其完成即获批
LAST_NODE_INDEX: int = max(cast(int, n["index"]) for n in ReviewNode.NODES)


def _now() -> datetime:
    return datetime.now(_TZ)


def _status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def _stage_label(stage: str) -> str:
    return STAGE_LABELS.get(stage, stage)


async def _write_system_log(db: AsyncSession, project_id: uuid.UUID, content: str) -> None:
    await project_repo.add_log(db, project_id=project_id, log_type="system", content=content)


async def _resolve_user_names(db: AsyncSession, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not user_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u.name for u in result.scalars().all()}


def _log_to_dict(log: ProjectProgressLog, names: dict[uuid.UUID, str]) -> dict[str, Any]:
    return {
        "id": log.id,
        "project_id": log.project_id,
        "log_type": log.log_type,
        "content": log.content,
        "created_by": log.created_by,
        "created_by_name": names.get(log.created_by) if log.created_by else None,
        "created_at": log.created_at,
    }


def _project_to_response_dict(
    project: RegistrationProject,
    latest_log: ProjectProgressLog | None,
    names: dict[uuid.UUID, str],
) -> dict[str, Any]:
    return {
        **{c.key: getattr(project, c.key) for c in RegistrationProject.__table__.columns},
        "latest_log": _log_to_dict(latest_log, names) if latest_log else None,
    }


# ── 查询 ──


async def get_projects(
    db: AsyncSession,
    *,
    search: str | None = None,
    registration_type: str | None = None,
    status: str | None = None,
    drug_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    projects = await project_repo.list_projects(
        db, search=search, registration_type=registration_type, status=status, drug_id=drug_id
    )
    latest = await project_repo.latest_logs_for_projects(db, [p.id for p in projects])
    user_ids = {log.created_by for log in latest.values() if log.created_by}
    names = await _resolve_user_names(db, user_ids)
    return [_project_to_response_dict(p, latest.get(p.id), names) for p in projects]


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> RegistrationProject:
    project = await project_repo.get_project_by_id(db, project_id)
    if not project:
        raise ValueError("项目不存在")
    return project


async def get_project_detail(db: AsyncSession, project_id: uuid.UUID) -> dict[str, Any]:
    project = await get_project(db, project_id)
    latest = await project_repo.latest_logs_for_projects(db, [project.id])
    log = latest.get(project.id)
    names = await _resolve_user_names(db, {log.created_by} if log and log.created_by else set())
    return _project_to_response_dict(project, log, names)


async def get_kpi(db: AsyncSession) -> dict[str, int]:
    due_before = date.today() + timedelta(days=30)
    return await project_repo.count_kpi(db, due_before)


async def get_project_logs(db: AsyncSession, project_id: uuid.UUID) -> list[dict[str, Any]]:
    await get_project(db, project_id)
    logs = await project_repo.list_logs(db, project_id)
    names = await _resolve_user_names(db, {log.created_by for log in logs if log.created_by})
    return [_log_to_dict(log, names) for log in logs]


# ── 创建 / 更新 / 删除 ──


async def create_project(
    db: AsyncSession,
    data: ProjectCreate,
    created_by: uuid.UUID | None = None,
) -> RegistrationProject:
    payload = data.model_dump(exclude_unset=True)
    if not payload.get("project_no"):
        payload["project_no"] = await project_repo.next_project_no(db, _now().year)
    payload["status"] = "draft"
    payload["pre_stage"] = "initiation"
    payload["stage_completed_at"] = {"initiation": _now().isoformat()}
    project = await project_repo.create_project(db, payload)
    await _write_system_log(db, project.id, "项目创建，初始状态：草稿")
    await db.commit()
    await db.refresh(project)
    if project.drug_id:
        await sync_from_drug(db, project.drug_id)
        await db.refresh(project)
    return project


async def update_project(db: AsyncSession, project_id: uuid.UUID, data: ProjectUpdate) -> RegistrationProject:
    project = await get_project(db, project_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    if project.drug_id:
        await sync_from_drug(db, project.drug_id)
        await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> None:
    project = await get_project(db, project_id)
    project.is_deleted = True
    await db.commit()


# ── 阶段推进（本页唯一状态入口，受理为界） ──


async def advance_stage(
    db: AsyncSession,
    project_id: uuid.UUID,
    target_stage: str,
) -> RegistrationProject:
    project = await get_project(db, project_id)
    if target_stage not in STAGE_ORDER[:4]:
        raise ValueError("「已受理」阶段只能由申报进度查询侧登记受理号后自动同步置达")
    if project.pre_stage == "accepted" or project.status in POST_ACCEPTANCE_STATUSES:
        raise ValueError("项目已受理，后续状态请在申报进度查询维护，此处只读")

    old_stage = project.pre_stage
    old_status = project.status
    if target_stage == old_stage:
        return project

    now = _now()
    completed: dict[str, Any] = dict(project.stage_completed_at or {})
    target_idx = STAGE_ORDER.index(target_stage)
    for idx, stage in enumerate(STAGE_ORDER):
        if idx <= target_idx:
            completed.setdefault(stage, now.isoformat())
        else:
            completed.pop(stage, None)
    project.stage_completed_at = completed
    project.pre_stage = target_stage
    new_status = STAGE_STATUS[target_stage]
    project.status = new_status
    if target_stage == "submission" and project.submitted_at is None:
        project.submitted_at = now.date()

    if new_status != old_status:
        await _write_system_log(db, project.id, f"{_status_label(old_status)} → {_status_label(new_status)}")
    else:
        direction = "阶段推进" if target_idx > STAGE_ORDER.index(old_stage) else "阶段回退"
        await _write_system_log(
            db, project.id, f"{direction}：{_stage_label(old_stage)} → {_stage_label(target_stage)}"
        )

    await db.commit()
    await db.refresh(project)
    return project


# ── 进展记录（只增不删） ──


async def add_progress_log(
    db: AsyncSession,
    project_id: uuid.UUID,
    content: str,
    created_by: uuid.UUID | None = None,
) -> dict[str, Any]:
    await get_project(db, project_id)
    log = await project_repo.add_log(
        db, project_id=project_id, log_type="manual", content=content, created_by=created_by
    )
    project = await get_project(db, project_id)
    project.latest_progress = content
    await db.commit()
    await db.refresh(log)
    names = await _resolve_user_names(db, {log.created_by} if log.created_by else set())
    return _log_to_dict(log, names)


# ── 申报进度查询侧同步 ──


def _desired_status_from_drug(drug: Drug, nodes: list[DrugNode]) -> str | None:
    """按品种受理信息 + 节点进度推导项目状态；返回 None 表示无需同步。

    受理触发条件严格为「取得受理号」（acceptance_date 是品种必填字段，不代表项目侧已受理）。
    获批判定与申报进度查询页一致：最后一个审评节点（获批时间）有实际完成日期。
    """
    if not drug.acceptance_number:
        return None
    effective_nodes = [n for n in nodes if not n.skipped]
    last_node = next((n for n in effective_nodes if n.node_index == LAST_NODE_INDEX), None)
    if last_node and last_node.actual_date:
        return "approved"
    completed = [n for n in effective_nodes if n.actual_date is not None]
    if not completed:
        return "accepted"
    # 发补节点（7 预计发补日期 / 8 发补递交）已发生且未获批 → 发补中
    deficiency = any(n.node_index in (7, 8) for n in completed)
    return "supplementary" if deficiency else "under_review"


async def sync_from_drug(db: AsyncSession, drug_id: uuid.UUID) -> int:
    """申报进度查询侧变化后回写关联项目状态（受理号登记 / 节点推进 / 审评结束）。

    每次状态变更自动写入 system 进展记录；撤回/终止状态不被同步覆盖。
    返回状态发生变更的项目数。
    """
    drug = await repo.get_drug_by_id(db, drug_id)
    if not drug:
        return 0

    projects = await project_repo.get_projects_by_drug(db, drug_id)
    if not projects:
        return 0

    # 节点走全新查询，避免会话内已加载的 drug.nodes 集合看不到同事务新增/修改的节点
    nodes = await repo.get_drug_nodes(db, drug_id)

    changed = 0
    for project in projects:
        if project.status in ("withdrawn", "terminated"):
            continue
        desired = _desired_status_from_drug(drug, nodes)
        now = _now()

        if desired in SYNC_TARGET_STATUSES and desired != project.status:
            await _write_system_log(db, project.id, f"{_status_label(project.status)} → {_status_label(desired)}")
            project.status = desired
            changed += 1

        if project.status in POST_ACCEPTANCE_STATUSES:
            # 受理信息回写：受理号、受理日期、阶段置达「已受理」
            if drug.acceptance_number and project.acceptance_number != drug.acceptance_number:
                project.acceptance_number = drug.acceptance_number
            if project.accepted_at != drug.acceptance_date:
                project.accepted_at = drug.acceptance_date
            if project.pre_stage != "accepted":
                completed = dict(project.stage_completed_at or {})
                for stage in STAGE_ORDER:
                    completed.setdefault(stage, now.isoformat())
                project.stage_completed_at = completed
                project.pre_stage = "accepted"

        if project.status == "approved":
            last_dates = [n.actual_date for n in nodes if not n.skipped and n.actual_date]
            if last_dates and project.approved_at != max(last_dates):
                project.approved_at = max(last_dates)
            prediction = await predict_drug(db, drug)
            if (
                prediction.estimated_approval_date
                and project.expected_completion_at != prediction.estimated_approval_date
            ):
                project.expected_completion_at = prediction.estimated_approval_date

    if changed:
        await db.commit()
    return changed
