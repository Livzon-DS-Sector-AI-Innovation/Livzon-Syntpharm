"""隐患的首页工作台取数（审核待办 / 我参与的流程）。

口径：
- 三级复核的 ``verify_level_N_reviewer_id`` 只在复核动作发生时回填，事前判不出具体人，
  因此「待复核」只能按「状态推导到待复核级别 + 我具备 safety:hazard:manage」兜底；
- 「我负责的整改 / 我发现 / 我分管 / 我复核过」可按人精确判定（责任人列是真实 FK / UUID 列表）。

本文件只被 ``app.modules.safety.public_api`` 调用。
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import cast, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.safety.models import HazardReport
from app.platform.workbench.constants import MATCH_PERSON, MATCH_ROLE, MODULE_SAFETY
from app.shared.module_registry import MODULES_BY_CODE
from app.shared.workbench_types import WorkbenchItem, WorkbenchSourceResult

logger = logging.getLogger(__name__)

_MODULE_LABEL = MODULES_BY_CODE[MODULE_SAFETY].name

#: 前端路由（模块自有，平台层不参与拼接）
_HAZARD_DETAIL_PATH = "/safety/hazard/{id}"

#: 复核级别 → 环节文案（与 api/hazards.py 的 verify-level 说明一致）
_VERIFY_LEVEL_LABELS: dict[int, str] = {
    1: "部门负责人复核",
    2: "分管领导复核",
    3: "检查人员复核",
}

#: 整改进度中文（前端枚举同源，后端自持一份避免跨端漂移）
_RECTIFICATION_LABELS: dict[str, str] = {
    "pending": "待整改",
    "in_progress": "整改中",
    "replied": "待复核",
    "ai_reviewing": "AI 初审中",
    "level1_approved": "一级已通过",
    "level2_approved": "二级已通过",
    "level3_approved": "三级已通过",
    "rejected": "已驳回",
    "closed": "已关闭",
    "no_rectification_needed": "无需整改",
}


def _age_days(moment: datetime | None) -> int | None:
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max((datetime.now(UTC) - moment).days, 0)


def _pending_review_level(hazard: HazardReport) -> int | None:
    """推导「当前等待哪一级复核」，判不出来返回 None（与 service/hazard.py 的门禁一致）。"""
    if hazard.rectification_status == "replied" and hazard.ai_review_status == "completed":
        if hazard.verify_level_1_status == "pending":
            return 1
    if hazard.verify_level_1_status == "approved" and hazard.verify_level_2_status == "pending":
        return 2
    if hazard.verify_level_2_status in ("approved", "no_review_needed") and hazard.verify_level_3_status == "pending":
        return 3
    return None


def _item(
    hazard: HazardReport,
    *,
    match_kind: str,
    step_label: str | None,
    my_roles: tuple[str, ...] = (),
) -> WorkbenchItem:
    return WorkbenchItem(
        id=str(hazard.id),
        source="hazard",
        module_key=MODULE_SAFETY,
        module_label=_MODULE_LABEL,
        doc_type_label="隐患整改",
        title=hazard.key_defect or hazard.description or hazard.hazard_no,
        doc_no=hazard.hazard_no,
        status=hazard.rectification_status,
        status_label=_RECTIFICATION_LABELS.get(hazard.rectification_status, hazard.rectification_status),
        step_label=step_label,
        match_kind=match_kind,
        age_days=_age_days(hazard.updated_at),
        # 隐患没有统一的复核 SLA，不在首页臆造超期判定
        overdue=False,
        path=_HAZARD_DETAIL_PATH.format(id=hazard.id),
        my_roles=my_roles,
    )


async def list_hazard_review_todos(
    db: AsyncSession,
    *,
    granted: set[str],
    limit: int,
) -> WorkbenchSourceResult:
    """待复核隐患：三级复核共用一个权限码，判不出具体复核人时按同角色兜底。"""
    if "safety:hazard:manage" not in granted:
        return WorkbenchSourceResult()

    # SQL 只做粗筛（有任一级 pending），精确级别由 _pending_review_level 在内存判定，
    # 避免同一套门禁规则在 SQL 和 Python 两处维护、两处漂移。
    coarse = or_(
        HazardReport.verify_level_1_status == "pending",
        HazardReport.verify_level_2_status == "pending",
        HazardReport.verify_level_3_status == "pending",
    )
    stmt = (
        select(HazardReport)
        .where(
            HazardReport.is_deleted.is_(False),  # noqa: E712
            HazardReport.status == "open",
            coarse,
        )
        .order_by(HazardReport.updated_at.asc())
        .limit(limit + 1)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    items: list[WorkbenchItem] = []
    for hazard in rows:
        level = _pending_review_level(hazard)
        if level is None:
            continue
        items.append(_item(hazard, match_kind=MATCH_ROLE, step_label=_VERIFY_LEVEL_LABELS.get(level)))
        if len(items) > limit:
            break
    return WorkbenchSourceResult(items=items[:limit], has_more=len(items) > limit)


async def list_hazard_processes(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    granted: set[str],
    limit: int,
) -> WorkbenchSourceResult:
    """我参与且未关闭的隐患：整改负责人 / 发现人 / 分管安全员 / 复核人。"""
    if "safety:hazard:read" not in granted:
        return WorkbenchSourceResult()

    user_text = str(user_id)
    stmt = (
        select(HazardReport)
        .where(
            HazardReport.is_deleted.is_(False),  # noqa: E712
            HazardReport.status == "open",
            or_(
                HazardReport.rectification_responsible_person == user_id,
                HazardReport.discovered_by == user_id,
                HazardReport.safety_officer_id == user_id,
                HazardReport.verify_level_1_reviewer_id == user_id,
                HazardReport.verify_level_2_reviewer_id == user_id,
                HazardReport.verify_level_3_reviewer_id == user_id,
                cast(HazardReport.rectification_responsible_person_ids, JSONB).contains([user_text]),
            ),
        )
        .order_by(HazardReport.updated_at.desc())
        .limit(limit + 1)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    items: list[WorkbenchItem] = []
    for hazard in rows[:limit]:
        roles: list[str] = []
        if hazard.rectification_responsible_person == user_id or user_text in (
            hazard.rectification_responsible_person_ids or []
        ):
            roles.append("整改负责人")
        if hazard.discovered_by == user_id:
            roles.append("发现人")
        if hazard.safety_officer_id == user_id:
            roles.append("分管安全员")
        if user_id in (
            hazard.verify_level_1_reviewer_id,
            hazard.verify_level_2_reviewer_id,
            hazard.verify_level_3_reviewer_id,
        ):
            roles.append("复核人")
        level = _pending_review_level(hazard)
        items.append(
            _item(
                hazard,
                match_kind=MATCH_PERSON,
                step_label=_VERIFY_LEVEL_LABELS.get(level) if level else None,
                my_roles=tuple(roles),
            )
        )
    return WorkbenchSourceResult(items=items, has_more=len(rows) > limit)
