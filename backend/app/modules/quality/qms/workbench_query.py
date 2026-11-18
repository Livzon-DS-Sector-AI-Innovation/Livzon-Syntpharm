"""质量模块的工作台取数实现（首页「审核待办 / 我参与的流程」）。

口径说明：
- 偏差台账：唯一能按人精确判定的流程（部门联系人 + ``resolve_step_handlers``），
  退回单以 ``returned_step`` 为准；只有解析不出处理人的环节（AI 分析）才按权限码兜底。
- 检验类（IQC/IPQC/FQC/取样/稳定性）：审批记录的 ``approver_id`` 是审批时回填的，
  提交时为空，无法事前判定具体人 → 只能「待审 + 我具备 :approve 权限」兜底。
- 仪器/校准记录：审批动作完全不落审批记录表，按单据状态兜底。
- CAPA：审批人字段全仓零预置，且前端暂无页面（path 留空）。

本文件只被 ``app.modules.quality.public_api`` 调用，平台层不得直接 import。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.modules.quality.qms.capa_models import Capa
from app.modules.quality.qms.deviation_department_models import DepartmentContact
from app.modules.quality.qms.deviation_flow import (
    STATUS_TO_STEP,
    STEP_DEFS,
    HandlerDirectory,
    allowed_actors,
    load_contacts,
    resolve_step_handlers,
)
from app.modules.quality.qms.deviation_ledger_constants import (
    STEP_OVERDUE_DAYS,
    LedgerStatus,
    status_label,
)
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger
from app.modules.quality.qms.fqc_models import FQCApprovalRecord, FQCInspection
from app.modules.quality.qms.instrument_models import InstrumentCalibration, InstrumentCalibrationRecord
from app.modules.quality.qms.ipqc_models import IPQCApprovalRecord, IPQCInspection
from app.modules.quality.qms.iqc_models import IQCApprovalRecord, IQCInspection
from app.modules.quality.qms.sampling_models import SamplingApprovalRecord, SamplingOrder
from app.modules.quality.qms.stability_models import StabilityApprovalRecord, StabilityStudy
from app.shared.module_registry import MODULES_BY_CODE
from app.shared.workbench_types import (
    CANDIDATE_SCAN_LIMIT,
    MATCH_PERSON,
    MATCH_ROLE,
    MODULE_QUALITY,
    WorkbenchItem,
    WorkbenchSourceResult,
)

logger = logging.getLogger(__name__)

_MODULE_LABEL = MODULES_BY_CODE[MODULE_QUALITY].name

#: 前端路由（模块自有，平台层不参与拼接）
_DEVIATION_DETAIL_PATH = "/quality/deviation/{id}"
_IQC_LIST_PATH = "/quality/iqc"
_IPQC_LIST_PATH = "/quality/ipqc"
_FQC_LIST_PATH = "/quality/fqc"
_SAMPLING_LIST_PATH = "/quality/sampling"
_STABILITY_LIST_PATH = "/quality/stability"
_INSTRUMENT_LIST_PATH = "/quality/instrument"

#: 参与流程排除的终态（草稿不属于「进行中的流程」）
_PROCESS_EXCLUDED_STATUSES: tuple[str, ...] = (
    LedgerStatus.DRAFT.value,
    LedgerStatus.CLOSED.value,
    LedgerStatus.CANCELLED.value,
)

#: 检验类「已完结」状态（各单据状态机命名不完全一致，取并集排除）
_TERMINAL_INSPECTION_STATUSES: tuple[str, ...] = (
    "final_approved",
    "qa_final_approved",
    "released",
    "locked",
    "closed",
    "completed",
    "cancelled",
)

#: 待办候选：8 个待办环节 + 历史 returned 态（新语义退回表现为「状态=目标环节 + returned_step」）
_TODO_STATUSES: tuple[str, ...] = (
    LedgerStatus.PENDING_AI_ANALYSIS.value,
    LedgerStatus.PENDING_INVESTIGATION.value,
    LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value,
    LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
    LedgerStatus.PENDING_QA_REVIEW.value,
    LedgerStatus.PENDING_QA_HEAD_REVIEW.value,
    LedgerStatus.PENDING_QUALITY_HEAD_REVIEW.value,
    LedgerStatus.PENDING_FINAL_CODE.value,
    LedgerStatus.RETURNED.value,
)

#: 各检验类的审批级别 → 环节文案
_LEVEL_LABELS: dict[str, dict[int, str]] = {
    "iqc": {1: "待部门负责人审批", 2: "待QA审批", 3: "待质量负责人审批"},
    "ipqc": {1: "待车间负责人审批", 2: "待QC主管审批", 3: "待QA审批"},
    "fqc": {1: "待QC主管审批", 2: "待QA审批", 3: "待质量负责人审批"},
    "sampling": {1: "待仓储/生产确认", 2: "待QA审批", 3: "待质量负责人审批"},
    "stability": {1: "待研发主管审批", 2: "待QA审批", 3: "待质量负责人审批", 4: "待质量负责人审批"},
}

#: 审批角色 → 中文（approval_level 缺失时的兜底）
_ROLE_LABELS: dict[str, str] = {
    "department_head": "部门负责人",
    "workshop_head": "车间负责人",
    "qc_supervisor": "QC主管",
    "qa": "QA",
    "quality_head": "质量负责人",
    "warehouse_production": "仓储/生产",
    "developer_supervisor": "研发主管",
    "admin": "设备管理员",
}

#: CAPA 待审状态 → 中文
_CAPA_STATUS_LABELS: dict[str, str] = {
    "pending_dept_head_confirm": "待部门负责人确认",
    "pending_qa_review": "待QA审核",
    "pending_q_head_approval": "待质量负责人批准",
    "pending_evaluation": "待评估",
}

#: 待办取数只需要的列：偏差正文 / 附件 / 报告版本可能很大，不能整行加载
_TODO_COLUMNS = (
    DeviationLedger.id,
    DeviationLedger.code,
    DeviationLedger.final_code,
    DeviationLedger.title,
    DeviationLedger.department,
    DeviationLedger.status,
    DeviationLedger.returned_step,
    DeviationLedger.status_updated_at,
    DeviationLedger.reporter_id,
    DeviationLedger.handler_ids,
    DeviationLedger.cross_dept_reviewers,
)

#: 流程取数额外需要「我是否参与」的列
_PROCESS_COLUMNS = (*_TODO_COLUMNS, DeviationLedger.discoverer_id, DeviationLedger.review_opinions)


@dataclass(frozen=True, slots=True)
class _ApprovalSource:
    """一类「审批记录 + 父单」的待办取数配置。"""

    source: str
    approve_code: str
    doc_type_label: str
    path: str
    record_model: Any
    parent_model: Any
    join_on: Any
    doc_no_col: Any
    title_col: Any


@dataclass(frozen=True, slots=True)
class _OwnRecordSource:
    """一类「我发起/我负责」的单据流程取数配置。"""

    source: str
    read_code: str
    doc_type_label: str
    path: str
    role_label: str
    model: Any
    owner_col: Any
    doc_no_col: Any
    title_col: Any


_APPROVAL_SOURCES: tuple[_ApprovalSource, ...] = (
    _ApprovalSource(
        source="iqc",
        approve_code="quality:iqc:approve",
        doc_type_label="IQC 来料检验",
        path=_IQC_LIST_PATH,
        record_model=IQCApprovalRecord,
        parent_model=IQCInspection,
        join_on=IQCApprovalRecord.iqc_inspection_id == IQCInspection.id,
        doc_no_col=IQCInspection.inspection_no,
        title_col=func.coalesce(IQCInspection.material_name, IQCInspection.material_code),
    ),
    _ApprovalSource(
        source="ipqc",
        approve_code="quality:ipqc:approve",
        doc_type_label="IPQC 过程检验",
        path=_IPQC_LIST_PATH,
        record_model=IPQCApprovalRecord,
        parent_model=IPQCInspection,
        join_on=IPQCApprovalRecord.ipqc_inspection_id == IPQCInspection.id,
        doc_no_col=IPQCInspection.inspection_no,
        title_col=func.coalesce(IPQCInspection.product_name, IPQCInspection.product_code),
    ),
    _ApprovalSource(
        source="fqc",
        approve_code="quality:fqc:approve",
        doc_type_label="FQC 成品检验",
        path=_FQC_LIST_PATH,
        record_model=FQCApprovalRecord,
        parent_model=FQCInspection,
        join_on=FQCApprovalRecord.fqc_inspection_id == FQCInspection.id,
        doc_no_col=FQCInspection.inspection_no,
        title_col=func.coalesce(FQCInspection.product_name, FQCInspection.product_code),
    ),
    _ApprovalSource(
        source="sampling",
        approve_code="quality:sampling:approve",
        doc_type_label="取样单",
        path=_SAMPLING_LIST_PATH,
        record_model=SamplingApprovalRecord,
        parent_model=SamplingOrder,
        join_on=SamplingApprovalRecord.sampling_order_id == SamplingOrder.id,
        doc_no_col=SamplingOrder.order_no,
        title_col=func.coalesce(SamplingOrder.material_name, SamplingOrder.material_code),
    ),
    _ApprovalSource(
        source="stability",
        approve_code="quality:stability:approve",
        doc_type_label="稳定性试验",
        path=_STABILITY_LIST_PATH,
        record_model=StabilityApprovalRecord,
        parent_model=StabilityStudy,
        join_on=StabilityApprovalRecord.study_id == StabilityStudy.id,
        doc_no_col=StabilityStudy.study_no,
        title_col=func.coalesce(StabilityStudy.product_name, StabilityStudy.product_code),
    ),
)

_OWN_RECORD_SOURCES: tuple[_OwnRecordSource, ...] = (
    _OwnRecordSource(
        source="iqc",
        read_code="quality:iqc:read",
        doc_type_label="IQC 来料检验",
        path=_IQC_LIST_PATH,
        role_label="检验员",
        model=IQCInspection,
        owner_col=IQCInspection.inspector_id,
        doc_no_col=IQCInspection.inspection_no,
        title_col=func.coalesce(IQCInspection.material_name, IQCInspection.material_code),
    ),
    _OwnRecordSource(
        source="ipqc",
        read_code="quality:ipqc:read",
        doc_type_label="IPQC 过程检验",
        path=_IPQC_LIST_PATH,
        role_label="检验员",
        model=IPQCInspection,
        owner_col=IPQCInspection.inspector_id,
        doc_no_col=IPQCInspection.inspection_no,
        title_col=func.coalesce(IPQCInspection.product_name, IPQCInspection.product_code),
    ),
    _OwnRecordSource(
        source="fqc",
        read_code="quality:fqc:read",
        doc_type_label="FQC 成品检验",
        path=_FQC_LIST_PATH,
        role_label="检验员",
        model=FQCInspection,
        owner_col=FQCInspection.inspector_id,
        doc_no_col=FQCInspection.inspection_no,
        title_col=func.coalesce(FQCInspection.product_name, FQCInspection.product_code),
    ),
    _OwnRecordSource(
        source="sampling",
        read_code="quality:sampling:read",
        doc_type_label="取样单",
        path=_SAMPLING_LIST_PATH,
        role_label="取样人",
        model=SamplingOrder,
        owner_col=SamplingOrder.sampler_id,
        doc_no_col=SamplingOrder.order_no,
        title_col=func.coalesce(SamplingOrder.material_name, SamplingOrder.material_code),
    ),
    _OwnRecordSource(
        source="stability",
        read_code="quality:stability:read",
        doc_type_label="稳定性试验",
        path=_STABILITY_LIST_PATH,
        role_label="方案负责人",
        model=StabilityStudy,
        owner_col=StabilityStudy.developer_id,
        doc_no_col=StabilityStudy.study_no,
        title_col=func.coalesce(StabilityStudy.product_name, StabilityStudy.product_code),
    ),
)


def _age_days(moment: datetime | None) -> int | None:
    """停留天数（UTC，负数归零）。"""
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max((datetime.now(UTC) - moment).days, 0)


def _deviation_step(row: DeviationLedger) -> str | None:
    """当前环节：returned 态取 returned_step，其余按状态映射（与 service._current_step 一致）。"""
    if row.status == LedgerStatus.RETURNED.value and row.returned_step:
        return row.returned_step
    return STATUS_TO_STEP.get(row.status) or row.returned_step


def _deviation_item(
    row: DeviationLedger,
    *,
    step: str,
    match_kind: str,
    my_roles: tuple[str, ...] = (),
) -> WorkbenchItem:
    step_def = STEP_DEFS.get(step)
    returned = bool(row.returned_step)
    step_label = step_def.label if step_def else step
    if returned:
        step_label = f"{step_label}（已退回）"
    threshold = STEP_OVERDUE_DAYS.get(row.status, 3)
    age = _age_days(row.status_updated_at)
    return WorkbenchItem(
        id=str(row.id),
        source="deviation",
        module_key=MODULE_QUALITY,
        module_label=_MODULE_LABEL,
        doc_type_label="偏差台账",
        title=row.title,
        doc_no=row.final_code or row.code,
        status=row.status,
        status_label=status_label(row.status),
        step_label=step_label,
        match_kind=match_kind,
        age_days=age,
        overdue=age is not None and age >= threshold,
        path=_DEVIATION_DETAIL_PATH.format(id=row.id),
        my_roles=my_roles,
    )


async def _load_candidate_directory(
    db: AsyncSession,
    rows: list[DeviationLedger],
) -> tuple[dict[str, DepartmentContact], HandlerDirectory]:
    """一次加载部门联系人 + 全部候选行的相关用户（避免逐行查库）。"""
    contacts = await load_contacts(db)
    uuid_ids: set[uuid.UUID] = set()
    cross_rows: list[dict[str, Any]] = []
    for row in rows:
        uuid_ids.update(row.handler_ids or [])
        uuid_ids.add(row.reporter_id)
        for entry in row.cross_dept_reviewers or []:
            if isinstance(entry, dict):
                cross_rows.append(entry)
    directory = await HandlerDirectory.load_for_ids(db, contacts, uuid_ids, cross_rows)
    return contacts, directory


async def list_deviation_todos(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    granted: set[str],
    limit: int,
) -> WorkbenchSourceResult:
    """偏差台账待办：当前环节处理人=我（精确），AI 分析环节按权限码兜底。"""
    if "quality:deviation:read" not in granted:
        return WorkbenchSourceResult()

    stmt = (
        select(DeviationLedger)
        .options(load_only(*_TODO_COLUMNS))
        .where(
            DeviationLedger.is_deleted.is_(False),
            DeviationLedger.status.not_in(_PROCESS_EXCLUDED_STATUSES),
            or_(
                DeviationLedger.status.in_(_TODO_STATUSES),
                DeviationLedger.returned_step.is_not(None),
            ),
        )
        .order_by(DeviationLedger.status_updated_at.asc())
        .limit(CANDIDATE_SCAN_LIMIT)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    if not rows:
        return WorkbenchSourceResult()
    if len(rows) >= CANDIDATE_SCAN_LIMIT:
        logger.warning(
            "workbench 偏差待办候选触顶，可能存在未纳入的待办",
            extra={"scan_limit": CANDIDATE_SCAN_LIMIT, "biz_module": "workbench"},
        )

    contacts, directory = await _load_candidate_directory(db, rows)
    matched: list[WorkbenchItem] = []
    for row in rows:
        step = _deviation_step(row)
        if not step or step not in STEP_DEFS:
            continue
        permission = STEP_DEFS[step].permission
        if permission not in granted:
            continue
        handlers = resolve_step_handlers(row, contacts, directory)
        allowed = allowed_actors(row, step, handlers)
        if user_id in allowed:
            matched.append(_deviation_item(row, step=step, match_kind=MATCH_PERSON))
        elif not handlers.get(step):
            # 解析不出具体处理人（AI 分析 / 联系人未配置）：只能按权限码兜底
            matched.append(_deviation_item(row, step=step, match_kind=MATCH_ROLE))

    return WorkbenchSourceResult(items=matched[:limit], has_more=len(matched) > limit)


async def list_deviation_processes(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    granted: set[str],
    limit: int,
) -> WorkbenchSourceResult:
    """我参与且未完结的偏差台账（发起 / 发现 / 调查 / 审核 / 当前处理）。"""
    if "quality:deviation:read" not in granted:
        return WorkbenchSourceResult()

    stmt = (
        select(DeviationLedger)
        .options(load_only(*_PROCESS_COLUMNS))
        .where(
            DeviationLedger.is_deleted.is_(False),
            DeviationLedger.status.not_in(_PROCESS_EXCLUDED_STATUSES),
        )
        .order_by(DeviationLedger.status_updated_at.desc())
        .limit(CANDIDATE_SCAN_LIMIT)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    if not rows:
        return WorkbenchSourceResult()

    contacts, directory = await _load_candidate_directory(db, rows)
    matched: list[WorkbenchItem] = []
    for row in rows:
        step = _deviation_step(row)
        roles: list[str] = []
        if row.reporter_id == user_id:
            roles.append("发起人")
        if row.discoverer_id == user_id:
            roles.append("发现人")
        if user_id in (row.handler_ids or []):
            roles.append("调查人")
        for entry in row.cross_dept_reviewers or []:
            if not isinstance(entry, dict):
                continue
            tokens = [token for token in (entry.get("investigator_ids") or []) if token]
            if user_id in directory.resolve(tokens) and "跨部门调查人" not in roles:
                roles.append("跨部门调查人")
        for opinion in row.review_opinions or []:
            if isinstance(opinion, dict) and str(opinion.get("author_id") or "") == str(user_id):
                roles.append("审核人")
                break
        if step and step in STEP_DEFS:
            handlers = resolve_step_handlers(row, contacts, directory)
            if user_id in allowed_actors(row, step, handlers):
                roles.append("当前处理人")
        if not roles:
            continue
        matched.append(
            _deviation_item(
                row,
                step=step or "investigation",
                match_kind=MATCH_PERSON,
                my_roles=tuple(dict.fromkeys(roles)),
            )
        )

    return WorkbenchSourceResult(items=matched[:limit], has_more=len(matched) > limit)


def _pending_approval_stmt(spec: _ApprovalSource, limit: int) -> Any:
    """构造「待审审批记录 + 父单信息」查询（列名统一，供 ``_collect_pending_approvals`` 消费）。"""
    return (
        select(
            spec.parent_model.id.label("parent_id"),
            spec.doc_no_col.label("doc_no"),
            spec.title_col.label("title"),
            spec.parent_model.status.label("status"),
            spec.record_model.approval_level,
            spec.record_model.approver_role,
            spec.record_model.created_at.label("pending_since"),
        )
        .join(spec.parent_model, spec.join_on)
        .where(
            spec.record_model.approval_status == "pending",
            spec.record_model.is_deleted.is_(False),
            spec.parent_model.is_deleted.is_(False),
        )
        .order_by(spec.record_model.created_at.asc())
        .limit(limit + 1)
    )


async def _collect_pending_approvals(
    db: AsyncSession,
    stmt: Any,
    *,
    source: str,
    doc_type_label: str,
    path: str,
    limit: int,
) -> WorkbenchSourceResult:
    """待审记录 → 待办条目（按审批级别给环节文案，判定依据固定为同角色）。"""
    rows = (await db.execute(stmt)).all()
    has_more = len(rows) > limit
    level_labels = _LEVEL_LABELS.get(source, {})
    items: list[WorkbenchItem] = []
    for row in rows[:limit]:
        level = int(row.approval_level or 0)
        step_label = level_labels.get(level) or _ROLE_LABELS.get(str(row.approver_role or ""), "待审批")
        items.append(
            WorkbenchItem(
                id=str(row.parent_id),
                source=source,
                module_key=MODULE_QUALITY,
                module_label=_MODULE_LABEL,
                doc_type_label=doc_type_label,
                title=str(row.title or row.doc_no or "-"),
                doc_no=str(row.doc_no) if row.doc_no else None,
                status=str(row.status or ""),
                status_label="待审批",
                step_label=step_label,
                match_kind=MATCH_ROLE,
                age_days=_age_days(row.pending_since),
                path=path,
            )
        )
    return WorkbenchSourceResult(items=items, has_more=has_more)


async def list_inspection_todos(
    db: AsyncSession,
    *,
    granted: set[str],
    limit: int,
) -> WorkbenchSourceResult:
    """检验类待办：按「审批记录待审 + 我具备该类审批权限」兜底（判不出具体人）。"""
    items: list[WorkbenchItem] = []
    has_more = False
    for spec in _APPROVAL_SOURCES:
        if spec.approve_code not in granted:
            continue
        result = await _collect_pending_approvals(
            db,
            _pending_approval_stmt(spec, limit),
            source=spec.source,
            doc_type_label=spec.doc_type_label,
            path=spec.path,
            limit=limit,
        )
        items.extend(result.items)
        has_more = has_more or result.has_more

    if "quality:instrument:approve" in granted:
        result = await _instrument_todos(db, limit=limit)
        items.extend(result.items)
        has_more = has_more or result.has_more

    return WorkbenchSourceResult(items=items[:limit], has_more=has_more or len(items) > limit)


async def _instrument_todos(db: AsyncSession, *, limit: int) -> WorkbenchSourceResult:
    """仪器 / 校准记录待审（审批动作不落审批记录表，只能按状态兜底）。"""
    instrument_rows = (
        await db.execute(
            select(
                InstrumentCalibration.id.label("parent_id"),
                InstrumentCalibration.instrument_no.label("doc_no"),
                InstrumentCalibration.instrument_name.label("title"),
                InstrumentCalibration.status.label("status"),
                InstrumentCalibration.updated_at.label("pending_since"),
            )
            .where(
                InstrumentCalibration.is_deleted.is_(False),
                InstrumentCalibration.status.in_(("submitted", "qa_approved")),
            )
            .order_by(InstrumentCalibration.updated_at.asc())
            .limit(limit + 1)
        )
    ).all()
    record_rows = (
        await db.execute(
            select(
                InstrumentCalibrationRecord.id.label("parent_id"),
                InstrumentCalibrationRecord.calibration_no.label("doc_no"),
                InstrumentCalibrationRecord.calibration_no.label("title"),
                InstrumentCalibrationRecord.status.label("status"),
                InstrumentCalibrationRecord.updated_at.label("pending_since"),
            )
            .where(
                InstrumentCalibrationRecord.is_deleted.is_(False),
                InstrumentCalibrationRecord.status.in_(("submitted", "qa_approved")),
            )
            .order_by(InstrumentCalibrationRecord.updated_at.asc())
            .limit(limit + 1)
        )
    ).all()

    items: list[WorkbenchItem] = []
    for row in instrument_rows[:limit]:
        step_label = "待设备管理员审核" if row.status == "submitted" else "待QA审核"
        items.append(
            WorkbenchItem(
                id=str(row.parent_id),
                source="instrument",
                module_key=MODULE_QUALITY,
                module_label=_MODULE_LABEL,
                doc_type_label="仪器档案",
                title=str(row.title or row.doc_no or "-"),
                doc_no=str(row.doc_no) if row.doc_no else None,
                status=str(row.status or ""),
                status_label="待审批",
                step_label=step_label,
                match_kind=MATCH_ROLE,
                age_days=_age_days(row.pending_since),
                path=_INSTRUMENT_LIST_PATH,
            )
        )
    for row in record_rows[:limit]:
        step_label = "校准记录待设备管理员审核" if row.status == "submitted" else "校准记录待QA审核"
        items.append(
            WorkbenchItem(
                id=str(row.parent_id),
                source="instrument_record",
                module_key=MODULE_QUALITY,
                module_label=_MODULE_LABEL,
                doc_type_label="仪器校准记录",
                title=str(row.title or row.doc_no or "-"),
                doc_no=str(row.doc_no) if row.doc_no else None,
                status=str(row.status or ""),
                status_label="待审批",
                step_label=step_label,
                match_kind=MATCH_ROLE,
                age_days=_age_days(row.pending_since),
                path=_INSTRUMENT_LIST_PATH,
            )
        )
    has_more = len(instrument_rows) > limit or len(record_rows) > limit
    return WorkbenchSourceResult(items=items[:limit], has_more=has_more)


async def list_inspection_processes(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    granted: set[str],
    limit: int,
) -> WorkbenchSourceResult:
    """我发起且未完结的检验 / 取样 / 稳定性单据（我是检验员 / 取样人 / 方案负责人）。"""
    items: list[WorkbenchItem] = []
    has_more = False
    for spec in _OWN_RECORD_SOURCES:
        if spec.read_code not in granted:
            continue
        stmt = (
            select(
                spec.model.id.label("parent_id"),
                spec.doc_no_col.label("doc_no"),
                spec.title_col.label("title"),
                spec.model.status.label("status"),
                spec.model.updated_at.label("pending_since"),
            )
            .where(
                spec.model.is_deleted.is_(False),
                spec.owner_col == user_id,
                spec.model.status.not_in(_TERMINAL_INSPECTION_STATUSES),
            )
            .order_by(spec.model.updated_at.desc())
            .limit(limit + 1)
        )
        rows = (await db.execute(stmt)).all()
        has_more = has_more or len(rows) > limit
        for row in rows[:limit]:
            items.append(
                WorkbenchItem(
                    id=str(row.parent_id),
                    source=spec.source,
                    module_key=MODULE_QUALITY,
                    module_label=_MODULE_LABEL,
                    doc_type_label=spec.doc_type_label,
                    title=str(row.title or row.doc_no or "-"),
                    doc_no=str(row.doc_no) if row.doc_no else None,
                    status=str(row.status or ""),
                    status_label=str(row.status or ""),
                    step_label=None,
                    match_kind=MATCH_PERSON,
                    age_days=_age_days(row.pending_since),
                    path=spec.path,
                    my_roles=(spec.role_label,),
                )
            )
    return WorkbenchSourceResult(items=items[:limit], has_more=has_more or len(items) > limit)


async def list_capa_todos(
    db: AsyncSession,
    *,
    granted: set[str],
    limit: int,
) -> WorkbenchSourceResult:
    """CAPA 待办：审批人字段没有预置，只能按状态 + 权限码兜底；前端暂无页面。"""
    if "quality:capa:approve" not in granted:
        return WorkbenchSourceResult()

    pending_statuses = tuple(_CAPA_STATUS_LABELS)
    stmt = (
        select(Capa)
        .where(
            Capa.is_deleted.is_(False),
            Capa.status.in_(pending_statuses),
        )
        .order_by(Capa.status_updated_at.asc().nulls_last())
        .limit(limit + 1)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    items = [
        WorkbenchItem(
            id=str(row.id),
            source="capa",
            module_key=MODULE_QUALITY,
            module_label=_MODULE_LABEL,
            doc_type_label="CAPA",
            title=str(row.title or row.capa_code or "-"),
            doc_no=row.final_code or row.capa_code,
            status=str(row.status),
            status_label=_CAPA_STATUS_LABELS.get(str(row.status), str(row.status)),
            step_label=_CAPA_STATUS_LABELS.get(str(row.status)),
            match_kind=MATCH_ROLE,
            age_days=_age_days(row.status_updated_at or row.created_at),
            path=None,
        )
        for row in rows[:limit]
    ]
    return WorkbenchSourceResult(items=items, has_more=len(rows) > limit)
