"""偏差台账业务层：视图组装、流转编排、附件、统计与候选数据。

流转规则全部下沉到 ``deviation_flow``；本层负责：

- 组装详情（步骤条、处理人、审核时间线、报告、附件）；
- 在事务内解析处理人、调用 ``transition()``，提交后再异步发飞书通知；
- 报告版本、附件（MinIO）、批量状态、软删除。
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from typing import Any, NamedTuple, cast

from fastapi import UploadFile
from sqlalchemy import CursorResult, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.llm import llm_client
from app.modules.hr import public_api as hr_public_api
from app.platform.identity.models import User
from app.shared.file_conversion import get_file_conversion

from . import deviation_ledger_constants as constants
from . import deviation_notify as notify
from .deviation_flow import (
    CROSS_DEPT_ROW_APPROVED,
    CROSS_DEPT_ROW_PENDING,
    CROSS_DEPT_STEP,
    REJECTED,
    RESUBMITTED,
    STATUS_TO_STEP,
    STEP_DEFS,
    FlowContext,
    HandlerDirectory,
    HandlerRef,
    TransitionOutcome,
    approve_cross_dept_row,
    build_flow_context,
    cross_dept_review_rows,
    cross_dept_row_payloads,
    cross_dept_row_reviewer_ids,
    is_cross_dept_row_approved,
    load_contacts,
    resolve_step_handlers,
    step_note,
    submit_final_code,
    transition,
)
from .deviation_ledger_constants import LedgerStatus
from .deviation_ledger_models import DeviationAttachmentComment, DeviationLedger
from .deviation_ledger_repository import DeviationAttachmentCommentRepository, DeviationLedgerRepository
from .deviation_ledger_schemas import (
    AiAnalysisData,
    AttachmentCommentCreateRequest,
    AttachmentCommentItem,
    AttachmentCommentListData,
    AttachmentCommentSummaryData,
    AttachmentCommentSummaryItem,
    AttachmentCommentUpdateRequest,
    AttachmentItem,
    BatchStatusRequest,
    CapaProposalItem,
    CompleteAiAnalysisRequest,
    CrossDeptApproveRequest,
    CrossDeptReviewerItem,
    CrossDeptStepSubItem,
    DeleteResultData,
    DistributionItem,
    FinalCodeRequest,
    InvestigationRecordItem,
    InvestigationRequest,
    LedgerCreateRequest,
    LedgerDetail,
    LedgerItem,
    LedgerStatisticsData,
    LedgerStep,
    LedgerUpdateRequest,
    OptionItem,
    ReportSaveRequest,
    ReportVersionItem,
    ResubmitRequest,
    ReviewOpinionItem,
    ReviewRequest,
    StatusDistributionItem,
    StepBreakdownItem,
    StepHandlerPerson,
)

logger = logging.getLogger(__name__)

#: 编号唯一冲突的最大重试次数（并发创建时的兜底）
_MAX_CODE_RETRY = 3

#: 附件上限 20MB
_MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024

#: 允许上传的附件类型
_ALLOWED_ATTACHMENT_TYPES: tuple[str, ...] = (
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "application/zip",
)

_STORAGE_MODULE = "quality"

#: 终态偏差（已关闭 / 已取消）的批注只读，仅可查阅
_COMMENT_FROZEN_STATUSES: tuple[str, ...] = (LedgerStatus.CLOSED.value, LedgerStatus.CANCELLED.value)

#: 批注「待处理」状态值
_COMMENT_STATUS_OPEN = "open"
_COMMENT_STATUS_RESOLVED = "resolved"

#: 可直接在线预览的图片类型
_PREVIEW_IMAGE_TYPES: tuple[str, ...] = ("image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp")
_PREVIEW_IMAGE_SUFFIXES: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
_PDF_CONTENT_TYPE = "application/pdf"
_DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_DOC_CONTENT_TYPE = "application/msword"

#: .doc→docx 预览转换的单飞锁（key = ledger_id:file_id），避免并发重复转换
_PREVIEW_LOCKS: dict[str, asyncio.Lock] = {}
_PREVIEW_LOCKS_GUARD = threading.Lock()
_PREVIEW_LOCKS_LIMIT = 256


def _preview_lock(key: str) -> asyncio.Lock:
    with _PREVIEW_LOCKS_GUARD:
        lock = _PREVIEW_LOCKS.get(key)
        if lock is None:
            if len(_PREVIEW_LOCKS) >= _PREVIEW_LOCKS_LIMIT:
                for stale_key in [k for k, v in _PREVIEW_LOCKS.items() if not v.locked()]:
                    _PREVIEW_LOCKS.pop(stale_key, None)
            lock = asyncio.Lock()
            _PREVIEW_LOCKS[key] = lock
        return lock

#: 可编辑基础信息的状态
_EDITABLE_STATUSES = (LedgerStatus.PENDING_AI_ANALYSIS.value, LedgerStatus.RETURNED.value)

_REVIEW_STEPS = (
    "dept_head_review",
    "cross_dept_head_review",
    "qa_review",
    "qa_head_review",
    "quality_head_review",
)

#: 允许调查人补录调查记录 / 维护调查文档的环节（调查中 + 全部审核环节）
_INVESTIGATION_EDIT_STEPS: tuple[str, ...] = ("investigation", *_REVIEW_STEPS)

#: 允许调查人维护调查文档（附件上传 / 删除）的环节，额外包含待 AI 分析（调查报告在此阶段填写）
_INVESTIGATION_DOC_STEPS: tuple[str, ...] = ("ai_analysis", *_INVESTIGATION_EDIT_STEPS)

#: 提交调查报告时隐式确认 AI 分析环节的审核意见正文
_AI_ANALYSIS_IMPLICIT_CONTENT = "AI 分析已完成，随调查报告提交"


def _normalized_cross_dept_rows(rows: Sequence[CrossDeptReviewerItem]) -> list[dict[str, Any]]:
    """跨部门行落库形态：只保留部门与调查人，审核进度由服务端逐行审批维护。"""
    return [
        {"department": row.department, "investigator_ids": [str(uid) for uid in row.investigator_ids]} for row in rows
    ]


def _merge_cross_dept_states(
    old_rows: Sequence[dict[str, Any]],
    new_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """名单更新后保留已通过行的审核状态（部门与调查人集合完全一致才保留）。"""
    approved_index: dict[tuple[str, frozenset[str]], dict[str, Any]] = {}
    for entry in old_rows:
        if not isinstance(entry, dict) or not is_cross_dept_row_approved(entry):
            continue
        key = (
            str(entry.get("department") or "").strip(),
            frozenset(str(token) for token in (entry.get("investigator_ids") or [])),
        )
        approved_index[key] = entry
    merged: list[dict[str, Any]] = []
    for entry in new_rows:
        key = (
            str(entry.get("department") or "").strip(),
            frozenset(str(token) for token in (entry.get("investigator_ids") or [])),
        )
        previous = approved_index.get(key)
        if previous is None:
            merged.append(dict(entry))
        else:
            merged.append(
                {
                    **entry,
                    "review_state": CROSS_DEPT_ROW_APPROVED,
                    "approved_by": previous.get("approved_by"),
                    "approved_name": previous.get("approved_name"),
                    "approved_at": previous.get("approved_at"),
                    "opinion": previous.get("opinion"),
                }
            )
    return merged


class DeviationLedgerService:
    """偏差台账服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DeviationLedgerRepository(db)
        self.comment_repo = DeviationAttachmentCommentRepository(db)

    # ── 列表 / 详情 ───────────────────────────────────────────────────

    async def list_items(
        self,
        *,
        status: str | None = None,
        department: str | None = None,
        reason_category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LedgerItem], int]:
        rows, total = await self.repo.list_items(
            status=status,
            department=department,
            reason_category=reason_category,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        contacts = await load_contacts(self.db)
        user_ids: set[uuid.UUID] = set()
        for row in rows:
            user_ids.add(row.discoverer_id)
            user_ids.add(row.reporter_id)
            user_ids.update(row.handler_ids or [])
        directory = await HandlerDirectory.load_for_ids(self.db, contacts, user_ids)
        profiles = {
            str(ref.id): _UserProfile(id=ref.id, name=ref.name, avatar_url=ref.avatar_url)
            for ref in directory.all_refs()
        }
        names = {key: profile.name for key, profile in profiles.items()}
        now = datetime.now(UTC)
        items = [self._to_item(row, names, profiles, contacts, directory, now) for row in rows]
        return items, total

    async def get_detail(
        self,
        ledger_id: uuid.UUID,
        *,
        viewer_id: uuid.UUID | None = None,
        viewer_is_superuser: bool = False,
    ) -> LedgerDetail:
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        return await self._build_detail(row, viewer_id=viewer_id, viewer_is_superuser=viewer_is_superuser)

    # ── 新建 ──────────────────────────────────────────────────────────

    async def create(self, payload: LedgerCreateRequest, *, user_id: uuid.UUID) -> LedgerDetail:
        """创建偏差：系统编号 + 发现人默认登录人（可指定实际发现人）+ 上报人取登录人。"""
        discoverer_id = payload.discoverer_id or user_id
        if discoverer_id != user_id:
            exists = await self.db.scalar(select(User.id).where(User.id == discoverer_id, User.is_deleted.is_(False)))  # noqa: E712
            if exists is None:
                raise BadRequestException("发现人不存在")
        last_error: IntegrityError | None = None
        for attempt in range(1, _MAX_CODE_RETRY + 1):
            today = date.today()
            code = await self.repo.next_daily_code(today)
            try:
                row = await self.repo.create(
                    code=code,
                    title=payload.title,
                    department=payload.department,
                    discovery_date=payload.discovery_date,
                    discovery_time=payload.discovery_time,
                    discovery_location=payload.discovery_location,
                    discoverer_id=discoverer_id,
                    affected_items=payload.affected_items,
                    batch_number=payload.batch_number,
                    description=payload.description,
                    status=constants.INITIAL_STATUS,
                    status_updated_at=datetime.now(UTC),
                    reporter_id=user_id,
                    handler_ids=payload.handler_ids,
                    needs_cross_dept_review=payload.needs_cross_dept_review,
                    cross_dept_reviewers=(
                        _normalized_cross_dept_rows(payload.cross_dept_reviewers)
                        if payload.needs_cross_dept_review
                        else None
                    ),
                    created_by=user_id,
                    updated_by=user_id,
                )
            except IntegrityError as exc:
                await self.db.rollback()
                last_error = exc
                logger.warning(
                    "deviation ledger code conflict, retrying",
                    extra={"app_module": "quality", "code": code, "attempt": attempt},
                )
                continue

            await self.db.commit()
            await self.db.refresh(row)
            logger.info(
                "deviation ledger created",
                extra={"app_module": "quality", "ledger_id": str(row.id), "code": row.code},
            )
            return await self._build_detail(row, viewer_id=user_id)

        logger.error(
            "deviation ledger code exhausted",
            extra={"app_module": "quality", "attempts": _MAX_CODE_RETRY},
        )
        raise BadRequestException("偏差编号生成冲突，请稍后重试") from last_error

    # ── 基础信息修改 ──────────────────────────────────────────────────

    async def update(
        self,
        ledger_id: uuid.UUID,
        payload: LedgerUpdateRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """待 AI 分析 / 已退回可改基础信息；待调查时调查人+上报人可单独调整跨部门配置。"""
        row = await self.repo.get_by_id_for_update(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        cross_dept_only = row.status == LedgerStatus.PENDING_INVESTIGATION.value
        if row.status not in _EDITABLE_STATUSES and not cross_dept_only:
            raise BadRequestException("当前状态不允许修改基础信息")
        if row.status == LedgerStatus.RETURNED.value and not actor_is_superuser:
            actors = set(row.handler_ids or []) | {row.reporter_id}
            if actor_id not in actors:
                raise ForbiddenException("只有上报人或调查人可以修改已退回偏差的基础信息")

        fields = payload.model_dump(exclude_unset=True)
        if cross_dept_only:
            allowed = {"needs_cross_dept_review", "cross_dept_reviewers"}
            if set(fields) - allowed:
                raise BadRequestException("调查阶段只能修改跨部门审核配置")
            if not actor_is_superuser:
                actors = set(row.handler_ids or []) | {row.reporter_id}
                if actor_id not in actors:
                    raise ForbiddenException("只有上报人或调查人可以调整跨部门审核配置")
        if "cross_dept_reviewers" in fields and fields["cross_dept_reviewers"] is not None:
            fields["cross_dept_reviewers"] = _merge_cross_dept_states(
                row.cross_dept_reviewers or [],
                _normalized_cross_dept_rows([CrossDeptReviewerItem(**item) for item in fields["cross_dept_reviewers"]]),
            )
        if fields.get("needs_cross_dept_review") is False:
            fields["cross_dept_reviewers"] = None
        for field_name, value in fields.items():
            if value is not None:
                setattr(row, field_name, value)
        if fields.get("needs_cross_dept_review") is False:
            #: 开关关闭时清空旧行，避免重新开启时复活过期名单
            row.cross_dept_reviewers = None
        row.status_updated_at = datetime.now(UTC)
        row.updated_by = actor_id
        await self.db.commit()
        await self.db.refresh(row)
        logger.info(
            "deviation ledger updated",
            extra={"app_module": "quality", "ledger_id": str(row.id), "actor": actor_name},
        )
        return await self._build_detail(row, viewer_id=actor_id, viewer_is_superuser=actor_is_superuser)

    # ── 流转 ──────────────────────────────────────────────────────────

    async def save_ai_analysis(
        self,
        ledger_id: uuid.UUID,
        payload: CompleteAiAnalysisRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """保存 AI 分析结果：只写库、不推进流程（流程由提交调查报告驱动）。"""
        row = await self.repo.get_by_id_for_update(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        if row.status not in _EDITABLE_STATUSES and not actor_is_superuser:
            raise BadRequestException("当前状态不允许保存 AI 分析结果")
        if not self._can_edit_analysis(row, actor_id, actor_is_superuser):
            raise ForbiddenException("仅上报人或调查人可保存 AI 分析结果")
        row.ai_analysis = payload.ai_analysis.model_dump(mode="json")
        row.updated_by = actor_id
        await self.db.commit()
        await self.db.refresh(row)
        logger.info(
            "deviation ai analysis saved",
            extra={"app_module": "quality", "ledger_id": str(ledger_id), "actor": actor_name},
        )
        return await self._build_detail(row, viewer_id=actor_id, viewer_is_superuser=actor_is_superuser)

    async def submit_investigation(
        self,
        ledger_id: uuid.UUID,
        payload: InvestigationRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """提交调查报告：待 AI 分析时先补齐「AI 分析」环节，再进入调查并提交部门负责人审核。"""
        row = await self.repo.get_by_id_for_update(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        #: 先构造记录以完成附件/字段校验，再有写库动作，避免校验失败后留下已流转状态
        record = self._build_investigation_record(row, payload, actor_id=actor_id, actor_name=actor_name)
        if row.status == LedgerStatus.PENDING_AI_ANALYSIS.value:
            #: AI 分析不再单独流转，随调查报告一并确认，形成完整的审计痕迹
            await transition(
                self.db,
                ledger_id=ledger_id,
                step="ai_analysis",
                result="approved",
                content=_AI_ANALYSIS_IMPLICIT_CONTENT,
                actor_id=actor_id,
                actor_name=actor_name,
                actor_is_superuser=actor_is_superuser,
            )
        row.investigation_records = [*(row.investigation_records or []), record]
        outcome = await transition(
            self.db,
            ledger_id=ledger_id,
            step="investigation",
            result="approved",
            content=record["nonconformity_description"],
            actor_id=actor_id,
            actor_name=actor_name,
            actor_is_superuser=actor_is_superuser,
        )
        self._schedule_transition_notice(outcome)
        return await self._build_detail(outcome.ledger, viewer_id=actor_id, viewer_is_superuser=actor_is_superuser)

    async def append_investigation_record(
        self,
        ledger_id: uuid.UUID,
        payload: InvestigationRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """审核阶段追加调查记录：只追加记录，不推进流程状态。"""
        row = await self.repo.get_by_id_for_update(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        step = row.returned_step if row.status == LedgerStatus.RETURNED.value else STATUS_TO_STEP.get(row.status)
        if step not in _INVESTIGATION_EDIT_STEPS and not actor_is_superuser:
            raise BadRequestException("当前状态不允许继续新增调查记录")
        actors = set(row.handler_ids or []) | {row.reporter_id}
        if not actor_is_superuser and actor_id not in actors:
            raise ForbiddenException("只有调查人可以新增调查记录")
        record = self._build_investigation_record(row, payload, actor_id=actor_id, actor_name=actor_name)
        row.investigation_records = [*(row.investigation_records or []), record]
        row.updated_by = actor_id
        await self.db.commit()
        await self.db.refresh(row)
        logger.info(
            "deviation investigation record appended",
            extra={"app_module": "quality", "ledger_id": str(ledger_id), "actor": actor_name},
        )
        return await self._build_detail(row, viewer_id=actor_id, viewer_is_superuser=actor_is_superuser)

    def _build_investigation_record(
        self,
        row: DeviationLedger,
        payload: InvestigationRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
    ) -> dict[str, Any]:
        """构造结构化调查记录：CAPA 序号回填、附件 file_id 引用校验快照。"""
        return {
            "nonconformity_description": payload.nonconformity_description.strip(),
            "root_cause_analysis": payload.root_cause_analysis.strip(),
            "risk_assessment": payload.risk_assessment.strip(),
            "capa_proposals": [
                {
                    "sequence": index,
                    "summary": capa.summary.strip(),
                    "executor": capa.executor,
                    "expected_completion_date": capa.expected_completion_date.isoformat()
                    if capa.expected_completion_date
                    else None,
                }
                for index, capa in enumerate(payload.capa_proposals, start=1)
            ],
            "urgent_measures": payload.urgent_measures,
            "attachments": self._resolve_attachment_snapshots(row, payload.attachment_file_ids),
            "author_id": str(actor_id),
            "author_name": actor_name,
            "create_time": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _resolve_attachment_snapshots(row: DeviationLedger, file_ids: Sequence[uuid.UUID]) -> list[dict[str, Any]]:
        """把记录引用的 file_id 解析为台账附件的展示快照（悬挂引用直接拒绝）。"""
        known = {str(entry.get("file_id")): entry for entry in (row.attachments or []) if isinstance(entry, dict)}
        snapshots: list[dict[str, Any]] = []
        for file_id in file_ids:
            entry = known.get(str(file_id))
            if entry is None:
                raise BadRequestException("调查记录附件不存在，请重新上传后再提交")
            snapshots.append(
                {
                    "file_id": str(entry.get("file_id")),
                    "file_name": str(entry.get("file_name") or "attachment"),
                    "size": int(entry.get("size") or 0),
                    "content_type": entry.get("content_type"),
                    "uploaded_by": entry.get("uploaded_by"),
                    "uploaded_by_name": entry.get("uploaded_by_name"),
                    "uploaded_at": entry.get("uploaded_at"),
                }
            )
        return snapshots

    async def approve_cross_dept(
        self,
        ledger_id: uuid.UUID,
        payload: CrossDeptApproveRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """跨部门逐行审批：全部行通过后环节才前进到所属 QA 审核。"""
        outcome = await approve_cross_dept_row(
            self.db,
            ledger_id=ledger_id,
            department=payload.department,
            content=payload.opinion,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_is_superuser=actor_is_superuser,
        )
        if outcome.next_status != outcome.previous_status:
            self._schedule_transition_notice(outcome)
        logger.info(
            "deviation cross-dept row approved",
            extra={
                "app_module": "quality",
                "ledger_id": str(ledger_id),
                "department": payload.department,
                "actor": actor_name,
            },
        )
        return await self._build_detail(
            outcome.ledger,
            viewer_id=actor_id,
            viewer_is_superuser=actor_is_superuser,
        )

    async def review(
        self,
        ledger_id: uuid.UUID,
        payload: ReviewRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """审核通过 / 退回。退回必须填写意见。"""
        step = payload.step or await self._current_review_step(ledger_id)
        if step not in _REVIEW_STEPS:
            raise BadRequestException("该环节不支持审核操作")
        if payload.result == REJECTED and not payload.content:
            raise BadRequestException("退回时必须填写审核意见")
        outcome = await transition(
            self.db,
            ledger_id=ledger_id,
            step=step,
            result=payload.result,
            content=payload.content,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_is_superuser=actor_is_superuser,
            reason_category=payload.reason_category,
            deviation_level=payload.deviation_level,
        )
        self._schedule_transition_notice(outcome)
        return await self._build_detail(outcome.ledger, viewer_id=actor_id)

    async def resubmit(
        self,
        ledger_id: uuid.UUID,
        payload: ResubmitRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """退回后重新提交，回到被退回的环节。"""
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        if row.status != LedgerStatus.RETURNED.value or not row.returned_step:
            raise BadRequestException("当前状态不允许重新提交")
        outcome = await transition(
            self.db,
            ledger_id=ledger_id,
            step=row.returned_step,
            result=RESUBMITTED,
            content=payload.content.strip() or "已按要求修改，重新提交",
            actor_id=actor_id,
            actor_name=actor_name,
            actor_is_superuser=actor_is_superuser,
        )
        self._schedule_transition_notice(outcome)
        return await self._build_detail(outcome.ledger, viewer_id=actor_id)

    async def submit_final_code(
        self,
        ledger_id: uuid.UUID,
        payload: FinalCodeRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """录入最终编号并关闭偏差。"""
        outcome = await submit_final_code(
            self.db,
            ledger_id=ledger_id,
            final_code=payload.final_code,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_is_superuser=actor_is_superuser,
        )
        notice = notify.to_notice(outcome.ledger, reporter_name=self._name_of(outcome, outcome.ledger.reporter_id))
        targets = outcome.directory.refs(list(outcome.ledger.handler_ids or []))
        reporter = outcome.directory.ref(outcome.ledger.reporter_id)
        if reporter is not None and all(ref.id != reporter.id for ref in targets):
            targets.append(reporter)
        notify.spawn(notify.notify_closed(notice, actor_name=actor_name, recipients=targets))
        return await self._build_detail(outcome.ledger, viewer_id=actor_id)

    # ── AI 分析 ──────────────────────────────────────────────────────

    async def generate_ai_analysis(self, ledger_id: uuid.UUID) -> AiAnalysisData:
        """调用大模型生成结构化分析（只返回不落库，由确认动作保存）。"""
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        if row.status not in _EDITABLE_STATUSES:
            raise BadRequestException("当前状态不需要重新生成 AI 分析")

        messages = _build_ai_messages(row)
        result = await llm_client.chat_json(
            messages,
            expected_keys=["description", "reason", "risk_assessment", "capa_suggestion"],
        )
        return AiAnalysisData(
            description=_text(result.get("description")),
            reason=_text(result.get("reason")),
            risk_assessment=_text(result.get("risk_assessment")),
            capa_suggestion=_text(result.get("capa_suggestion")),
            model="default",
            generated_at=datetime.now(UTC),
        )

    # ── 调查报告 ──────────────────────────────────────────────────────

    async def save_report(
        self,
        ledger_id: uuid.UUID,
        payload: ReportSaveRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """保存调查报告正文；默认追加一个版本记录。"""
        row = await self.repo.get_by_id_for_update(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        allowed_steps = ("investigation",)
        step = row.returned_step if row.status == LedgerStatus.RETURNED.value else STATUS_TO_STEP.get(row.status)
        if step not in allowed_steps and not actor_is_superuser:
            raise BadRequestException("当前状态不允许编辑调查报告")
        actors = set(row.handler_ids or []) | {row.reporter_id}
        if not actor_is_superuser and actors and actor_id not in actors:
            raise ForbiddenException("只有调查人可以编辑调查报告")

        row.report_content = payload.content
        if payload.append_version:
            row.report_versions = [
                *(row.report_versions or []),
                {
                    "content": payload.content,
                    "editor_id": str(actor_id),
                    "editor_name": actor_name,
                    "edit_time": datetime.now(UTC).isoformat(),
                    "change_summary": payload.change_summary,
                },
            ]
        row.updated_by = actor_id
        await self.db.commit()
        await self.db.refresh(row)
        return await self._build_detail(row, viewer_id=actor_id)

    # ── 附件 ──────────────────────────────────────────────────────────

    async def add_attachment(
        self,
        ledger_id: uuid.UUID,
        upload: UploadFile,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """上传附件：二进制进 MinIO，DB 只存元数据。"""
        row = await self.repo.get_by_id_for_update(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        self._assert_can_edit_investigation(row, actor_id, actor_is_superuser=actor_is_superuser)

        filename = os.path.basename((upload.filename or "attachment").strip()) or "attachment"
        content = await upload.read()
        if not content:
            raise BadRequestException("附件内容为空")
        if len(content) > _MAX_ATTACHMENT_BYTES:
            raise BadRequestException("单个附件不能超过 20MB")
        content_type = upload.content_type or "application/octet-stream"
        if content_type not in _ALLOWED_ATTACHMENT_TYPES:
            raise BadRequestException("不支持该附件类型")

        file_id = uuid.uuid4()
        object_key = f"deviation-ledger/{ledger_id}/{file_id}-{filename}"
        if not storage.is_enabled():
            raise BadRequestException("文件存储未配置，无法上传附件")
        storage.upload_object(_STORAGE_MODULE, object_key, content, len(content), content_type)
        row.attachments = [
            *(row.attachments or []),
            {
                "file_id": str(file_id),
                "file_name": filename,
                "object_key": object_key,
                "size": len(content),
                "content_type": content_type,
                "uploaded_by": str(actor_id),
                "uploaded_by_name": actor_name,
                "uploaded_at": datetime.now(UTC).isoformat(),
            },
        ]
        row.updated_by = actor_id
        await self.db.commit()
        await self.db.refresh(row)
        return await self._build_detail(row, viewer_id=actor_id)

    async def remove_attachment(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
        *,
        actor_id: uuid.UUID,
        actor_is_superuser: bool = False,
    ) -> LedgerDetail:
        """删除附件元数据与对象存储文件。"""
        row = await self.repo.get_by_id_for_update(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        self._assert_can_edit_investigation(row, actor_id, actor_is_superuser=actor_is_superuser)

        items = list(row.attachments or [])
        target = next((item for item in items if str(item.get("file_id")) == str(file_id)), None)
        if target is None:
            raise NotFoundException("附件不存在")
        referenced = any(
            isinstance(record, dict)
            and any(
                isinstance(att, dict) and str(att.get("file_id")) == str(file_id)
                for att in (record.get("attachments") or [])
            )
            for record in (row.investigation_records or [])
        )
        if referenced:
            raise BadRequestException("该附件已被调查记录引用，无法删除")
        row.attachments = [item for item in items if str(item.get("file_id")) != str(file_id)]
        row.updated_by = actor_id
        #: 附件删除后批注随之软删，避免孤儿批注继续出现在汇总里
        await self.comment_repo.soft_delete_by_file(ledger_id, file_id, actor_id=actor_id)
        await self.db.commit()
        await self.db.refresh(row)
        if storage.is_enabled():
            stale_keys = [str(target["object_key"])] if target.get("object_key") else []
            # 转换缓存按 file_id 生成，原文件删除后不再被引用，一并清理避免对象累积
            stale_keys.append(_preview_cache_key(ledger_id, file_id))
            for key in stale_keys:
                try:
                    await asyncio.to_thread(storage.delete_object, _STORAGE_MODULE, key)
                except Exception:  # noqa: BLE001 - 存储清理失败不回滚元数据
                    logger.warning(
                        "deviation attachment object delete failed",
                        extra={"app_module": "quality", "ledger_id": str(ledger_id), "object_key": key},
                    )
        return await self._build_detail(row, viewer_id=actor_id)

    async def get_attachment_file(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
    ) -> tuple[str, bytes, str]:
        """读取附件内容（校验归属，返回文件名 / 内容 / 类型）。"""
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        target = next(
            (item for item in (row.attachments or []) if str(item.get("file_id")) == str(file_id)),
            None,
        )
        if target is None:
            raise NotFoundException("附件不存在")
        if not storage.is_enabled():
            raise BadRequestException("文件存储未配置")
        found = storage.get_object(_STORAGE_MODULE, str(target.get("object_key")))
        if found is None:
            raise NotFoundException("附件文件已丢失")
        content, content_type = found
        return str(target.get("file_name") or "attachment"), content, content_type

    async def get_attachment_preview(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
    ) -> tuple[str, bytes, str]:
        """预览用字节流：pdf / docx / 图片直出，``.doc`` 转 docx 后返回（转换结果缓存到对象存储）。"""
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        target = self._find_attachment(row, file_id)
        if target is None:
            raise NotFoundException("附件不存在")
        if not storage.is_enabled():
            raise BadRequestException("文件存储未配置")

        file_name = str(target.get("file_name") or "attachment")
        content_type = str(target.get("content_type") or "")
        suffix = os.path.splitext(file_name)[1].lower()

        if content_type in _PREVIEW_IMAGE_TYPES or suffix in _PREVIEW_IMAGE_SUFFIXES:
            return file_name, await asyncio.to_thread(self._read_object, target), content_type or "image/png"
        if content_type == _PDF_CONTENT_TYPE or suffix == ".pdf":
            return file_name, await asyncio.to_thread(self._read_object, target), _PDF_CONTENT_TYPE
        if content_type == _DOCX_CONTENT_TYPE or suffix == ".docx":
            return file_name, await asyncio.to_thread(self._read_object, target), _DOCX_CONTENT_TYPE
        if content_type == _DOC_CONTENT_TYPE or suffix == ".doc":
            return await self._preview_legacy_doc(ledger_id, file_id, target, file_name)
        raise BadRequestException("该文件类型不支持在线预览")

    async def _preview_legacy_doc(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
        target: dict[str, Any],
        file_name: str,
    ) -> tuple[str, bytes, str]:
        """``.doc`` 预览：先查对象存储缓存，未命中则单飞转换并回写缓存。"""
        cache_key = _preview_cache_key(ledger_id, file_id)
        cached = await asyncio.to_thread(storage.get_object, _STORAGE_MODULE, cache_key)
        if cached is not None and cached[0]:
            return _docx_file_name(file_name), cached[0], _DOCX_CONTENT_TYPE

        async with _preview_lock(f"{ledger_id}:{file_id}"):
            cached = await asyncio.to_thread(storage.get_object, _STORAGE_MODULE, cache_key)
            if cached is not None and cached[0]:
                return _docx_file_name(file_name), cached[0], _DOCX_CONTENT_TYPE

            source = await asyncio.to_thread(self._read_object, target)
            converted = await asyncio.to_thread(get_file_conversion().convert_bytes_to_docx, source, file_name)
            if not converted:
                raise BadRequestException("该文档暂无法在线预览，请下载后查看")
            try:
                await asyncio.to_thread(
                    storage.upload_object,
                    _STORAGE_MODULE,
                    cache_key,
                    converted,
                    len(converted),
                    _DOCX_CONTENT_TYPE,
                )
            except Exception:  # noqa: BLE001 - 缓存失败不影响本次预览
                logger.warning(
                    "deviation preview cache write failed",
                    extra={"app_module": "quality", "ledger_id": str(ledger_id)},
                )
            return _docx_file_name(file_name), converted, _DOCX_CONTENT_TYPE

    @staticmethod
    def _read_object(target: dict[str, Any]) -> bytes:
        found = storage.get_object(_STORAGE_MODULE, str(target.get("object_key")))
        if found is None:
            raise NotFoundException("附件文件已丢失")
        return found[0]

    # ── 附件批注 ──────────────────────────────────────────────────────

    async def list_attachment_comments(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
    ) -> AttachmentCommentListData:
        """某附件的批注列表（时间正序，含未处理条数）。"""
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        if self._find_attachment(row, file_id) is None:
            raise NotFoundException("附件不存在")
        comments = await self.comment_repo.list_by_file(ledger_id, file_id)
        profiles = await self._load_comment_profiles(comments)
        items = [self._to_comment_item(comment, profiles) for comment in comments]
        return AttachmentCommentListData(
            items=items,
            total=len(items),
            open_count=sum(1 for item in items if item.status == _COMMENT_STATUS_OPEN),
        )

    async def add_attachment_comment(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
        payload: AttachmentCommentCreateRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
    ) -> AttachmentCommentItem:
        """新增批注：能查看该偏差即可留批注，终态偏差只读。"""
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        self._assert_comments_writable(row)
        target = self._find_attachment(row, file_id)
        if target is None:
            raise NotFoundException("附件不存在")
        comment = await self.comment_repo.create(
            ledger_id=ledger_id,
            file_id=file_id,
            file_name=str(target.get("file_name") or "attachment")[:255],
            page_no=payload.page_no,
            anchor_text=payload.anchor_text,
            content=payload.content,
            status=_COMMENT_STATUS_OPEN,
            author_name=actor_name,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self.db.commit()
        await self.db.refresh(comment)
        profiles = await self._load_comment_profiles([comment])
        return self._to_comment_item(comment, profiles)

    async def update_attachment_comment(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
        comment_id: uuid.UUID,
        payload: AttachmentCommentUpdateRequest,
        *,
        actor_id: uuid.UUID,
        actor_name: str,
        actor_is_superuser: bool = False,
    ) -> AttachmentCommentItem:
        """改内容仅限作者 / 超管；改处理状态（解决、重开）对所有读者开放。"""
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        self._assert_comments_writable(row)
        comment = await self.comment_repo.get(ledger_id, file_id, comment_id)
        if comment is None:
            raise NotFoundException("批注不存在")
        if payload.content is None and payload.status is None:
            raise BadRequestException("没有需要更新的内容")
        if payload.content is not None:
            if not actor_is_superuser and comment.created_by != actor_id:
                raise ForbiddenException("只能修改自己提交的批注")
            comment.content = payload.content
        if payload.status is not None:
            comment.status = payload.status
            if payload.status == _COMMENT_STATUS_RESOLVED:
                comment.resolved_by = actor_id
                comment.resolved_by_name = actor_name
                comment.resolved_at = datetime.now(UTC)
            else:
                comment.resolved_by = None
                comment.resolved_by_name = None
                comment.resolved_at = None
        comment.updated_by = actor_id
        await self.db.commit()
        await self.db.refresh(comment)
        profiles = await self._load_comment_profiles([comment])
        return self._to_comment_item(comment, profiles)

    async def delete_attachment_comment(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
        comment_id: uuid.UUID,
        *,
        actor_id: uuid.UUID,
        actor_is_superuser: bool = False,
    ) -> DeleteResultData:
        """软删除批注，仅作者本人或超管。"""
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        self._assert_comments_writable(row)
        comment = await self.comment_repo.get(ledger_id, file_id, comment_id)
        if comment is None:
            raise NotFoundException("批注不存在")
        if not actor_is_superuser and comment.created_by != actor_id:
            raise ForbiddenException("只能删除自己提交的批注")
        comment.is_deleted = True
        comment.updated_by = actor_id
        await self.db.commit()
        return DeleteResultData(id=comment_id, deleted=True)

    async def attachment_comment_summary(self, ledger_id: uuid.UUID) -> AttachmentCommentSummaryData:
        """详情页附件角标：按附件聚合未处理 / 全部批注数。"""
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        rows = await self.comment_repo.summary_by_ledger(ledger_id)
        return AttachmentCommentSummaryData(
            items=[
                AttachmentCommentSummaryItem(file_id=file_id, open_count=open_count, total_count=total_count)
                for file_id, open_count, total_count in rows
            ]
        )

    @staticmethod
    def _find_attachment(row: DeviationLedger, file_id: uuid.UUID) -> dict[str, Any] | None:
        """在主附件与调查记录附件快照中定位附件元数据。"""
        for item in row.attachments or []:
            if isinstance(item, dict) and str(item.get("file_id")) == str(file_id):
                return item
        for record in row.investigation_records or []:
            if not isinstance(record, dict):
                continue
            for att in record.get("attachments") or []:
                if isinstance(att, dict) and str(att.get("file_id")) == str(file_id):
                    return att
        return None

    @staticmethod
    def _assert_comments_writable(row: DeviationLedger) -> None:
        if row.status in _COMMENT_FROZEN_STATUSES:
            raise BadRequestException("偏差已关闭，批注不可修改")

    async def _load_comment_profiles(
        self, comments: Sequence[DeviationAttachmentComment]
    ) -> dict[str, _UserProfile]:
        ids: set[uuid.UUID] = set()
        for comment in comments:
            if comment.created_by is not None:
                ids.add(comment.created_by)
            if comment.resolved_by is not None:
                ids.add(comment.resolved_by)
        if not ids:
            return {}
        result = await self.db.execute(
            select(User.id, User.name, User.avatar_thumb, User.avatar_url).where(User.id.in_(ids))
        )
        return {
            str(user_id): _UserProfile(id=user_id, name=name or "-", avatar_url=avatar_thumb or avatar_url)
            for user_id, name, avatar_thumb, avatar_url in result.all()
        }

    @staticmethod
    def _to_comment_item(
        comment: DeviationAttachmentComment,
        profiles: dict[str, _UserProfile],
    ) -> AttachmentCommentItem:
        author = profiles.get(str(comment.created_by)) if comment.created_by else None
        return AttachmentCommentItem(
            id=comment.id,
            ledger_id=comment.ledger_id,
            file_id=comment.file_id,
            file_name=comment.file_name,
            page_no=comment.page_no,
            anchor_text=comment.anchor_text,
            content=comment.content,
            status=comment.status,
            author_id=comment.created_by,
            author_name=comment.author_name or (author.name if author else None),
            author_avatar=author.avatar_url if author else None,
            resolved_by=comment.resolved_by,
            resolved_by_name=comment.resolved_by_name,
            resolved_at=comment.resolved_at,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )

    # ── 批量 / 删除 ───────────────────────────────────────────────────

    async def batch_update_status(
        self,
        payload: BatchStatusRequest,
        *,
        actor_id: uuid.UUID,
    ) -> int:
        """批量更新状态（管理动作，不在流程内核内）。"""
        result = await self.db.execute(
            update(DeviationLedger)
            .where(
                DeviationLedger.id.in_(payload.ids),
                DeviationLedger.is_deleted.is_(False),  # noqa: E712
            )
            .values(
                status=payload.status,
                status_updated_at=datetime.now(UTC),
                updated_by=actor_id,
            )
        )
        await self.db.commit()
        return int(cast(CursorResult[Any], result).rowcount or 0)

    async def delete(self, ledger_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
        """软删除：任意状态均可删除，数据仅标记 ``is_deleted``，仍可追溯。"""
        row = await self.repo.get_by_id_for_update(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        row.is_deleted = True
        row.updated_by = actor_id
        await self.db.commit()
        logger.info(
            "deviation ledger soft deleted",
            extra={"app_module": "quality", "ledger_id": str(ledger_id), "status": row.status},
        )

    # ── 看盘统计 ──────────────────────────────────────────────────────

    async def statistics(self) -> LedgerStatisticsData:
        row = await self.repo.statistics()
        status_counts = dict(row.status_distribution)
        return LedgerStatisticsData(
            total=row.total,
            pending=row.pending,
            returned=row.returned,
            closed=row.closed,
            overdue=row.overdue,
            department_distribution=[
                DistributionItem(name=name, count=count) for name, count in row.department_distribution
            ],
            status_distribution=[
                StatusDistributionItem(status=status, label=constants.status_label(status), count=count)
                for status, count in row.status_distribution
            ],
            step_breakdown=[
                StepBreakdownItem(
                    step=definition.step,
                    label=definition.label,
                    role_label=definition.role_label,
                    status=definition.status,
                    count=status_counts.get(definition.status, 0),
                )
                for definition in STEP_DEFS.values()
            ],
        )

    # ── 候选数据 ──────────────────────────────────────────────────────

    async def contact_department_options(self) -> list[OptionItem]:
        """新建 / 编辑可用部门：只取部门联系人配置中的部门。

        环节负责人按部门名从 ``quality.department_contacts`` 解析，候选同源可保证
        新单一定能关联到节点处理人（与妙搭「新建偏差部门取自部门联系人」一致）。
        """
        contacts = await load_contacts(self.db)
        return [OptionItem(value=name, label=name) for name in sorted(contacts)]

    async def department_options(self) -> list[OptionItem]:
        """筛选栏部门候选：优先 hr.departments，空则回落用户档案里的部门去重。"""
        departments = await hr_public_api.list_all_departments(self.db)
        names = [dept.name for dept in departments if dept.name and not dept.is_deleted]
        if not names:
            rows = await self.db.execute(
                select(User.department)
                .where(
                    User.is_deleted.is_(False),  # noqa: E712
                    User.department.isnot(None),
                    User.department != "",
                )
                .distinct()
            )
            names = [str(value) for value in rows.scalars().all() if value]
        return [OptionItem(value=name, label=name) for name in sorted(set(names))]

    async def investigator_options(self, keyword: str | None = None, limit: int = 50) -> list[OptionItem]:
        """调查人候选：平台用户档案（姓名 + 部门）。"""
        stmt = select(User.id, User.name, User.department).where(User.is_deleted.is_(False))  # noqa: E712
        if keyword:
            stmt = stmt.where(User.name.ilike(f"%{keyword.strip()}%"))
        stmt = stmt.order_by(User.name.asc()).limit(limit)
        rows = (await self.db.execute(stmt)).all()
        return [OptionItem(value=str(row.id), label=row.name or "-", description=row.department) for row in rows]

    # ── 内部：详情组装 ────────────────────────────────────────────────

    async def _build_detail(
        self,
        row: DeviationLedger,
        *,
        viewer_id: uuid.UUID | None = None,
        viewer_is_superuser: bool = False,
    ) -> LedgerDetail:
        flow: FlowContext = await build_flow_context(self.db, row)
        opinion_ids, investigation_ids, uploader_ids, version_ids = _collect_detail_user_ids(row)
        extra_ids = set(opinion_ids) | set(investigation_ids) | set(uploader_ids) | set(version_ids)
        profiles = await self._load_user_profiles(row, extra_ids)
        names = {key: profile.name for key, profile in profiles.items()}
        now = datetime.now(UTC)
        item = self._to_item(row, names, profiles, flow.contacts, flow.directory, now)

        current_step = (
            row.returned_step if row.status == LedgerStatus.RETURNED.value else STATUS_TO_STEP.get(row.status)
        )
        actions = _allowed_actions(
            row,
            current_step,
            flow,
            viewer_id=viewer_id,
            viewer_is_superuser=viewer_is_superuser,
        )
        step_models = []
        for definition in STEP_DEFS.values():
            applicable, skip_reason, auto_skip = step_note(row, definition.step)
            step_models.append(
                LedgerStep(
                    step=definition.step,
                    label=definition.label,
                    status=definition.status,
                    role_label=definition.role_label,
                    handlers=[
                        StepHandlerPerson(id=ref.id, name=ref.name, avatar_url=ref.avatar_url)
                        for ref in flow.refs(definition.step)
                    ],
                    applicable=applicable,
                    skip_reason=skip_reason,
                    auto_skip=auto_skip,
                    sub_items=[
                        CrossDeptStepSubItem(**payload)
                        for payload in cross_dept_row_payloads(row, flow.contacts, flow.directory)
                    ]
                    if definition.step == CROSS_DEPT_STEP and applicable
                    else [],
                )
            )

        is_investigator = viewer_id is not None and (
            viewer_is_superuser or viewer_id == row.reporter_id or viewer_id in set(row.handler_ids or [])
        )
        investigation_step = (
            row.returned_step if row.status == LedgerStatus.RETURNED.value else STATUS_TO_STEP.get(row.status)
        )
        can_edit_investigation = is_investigator and (
            viewer_is_superuser or investigation_step in _INVESTIGATION_DOC_STEPS
        )
        editable = row.status == LedgerStatus.PENDING_AI_ANALYSIS.value or (
            row.status == LedgerStatus.RETURNED.value and is_investigator
        )
        can_edit_cross_dept = editable or (
            row.status == LedgerStatus.PENDING_INVESTIGATION.value
            and is_investigator
            and not any(is_cross_dept_row_approved(entry) for entry in cross_dept_review_rows(row))
        )

        return LedgerDetail(
            **item.model_dump(),
            discovery_time=row.discovery_time,
            discovery_location=row.discovery_location,
            discoverer_name=names.get(str(row.discoverer_id)),
            discoverer=_person(profiles, row.discoverer_id),
            affected_items=row.affected_items,
            batch_number=row.batch_number,
            description=row.description,
            needs_cross_dept_review=row.needs_cross_dept_review,
            reason_category=row.reason_category,
            handler_ids=list(row.handler_ids or []),
            cross_dept_reviewers=[
                self._build_cross_dept_item(entry, flow, names, row, viewer_id, viewer_is_superuser)
                for entry in cross_dept_review_rows(row)
            ],
            attachments=[
                AttachmentItem(
                    file_id=uuid.UUID(str(entry.get("file_id"))),
                    file_name=str(entry.get("file_name") or "attachment"),
                    size=int(entry.get("size") or 0),
                    content_type=entry.get("content_type"),
                    uploaded_by=_as_uuid(entry.get("uploaded_by")),
                    uploaded_by_name=entry.get("uploaded_by_name") or names.get(str(entry.get("uploaded_by"))),
                    uploaded_by_avatar=_avatar_of(profiles, entry.get("uploaded_by")),
                    uploaded_at=_as_datetime(entry.get("uploaded_at")),
                )
                for entry in (row.attachments or [])
                if _is_uuid(entry.get("file_id"))
            ],
            ai_analysis=AiAnalysisData(**row.ai_analysis) if row.ai_analysis else None,
            investigation_records=[
                InvestigationRecordItem(
                    content=str(entry.get("content") or ""),
                    nonconformity_description=str(entry.get("nonconformity_description") or ""),
                    root_cause_analysis=str(entry.get("root_cause_analysis") or ""),
                    risk_assessment=str(entry.get("risk_assessment") or ""),
                    capa_proposals=[
                        CapaProposalItem(**capa)
                        for capa in (entry.get("capa_proposals") or [])
                        if isinstance(capa, dict)
                    ],
                    urgent_measures=str(entry.get("urgent_measures") or "") or None,
                    attachments=[
                        AttachmentItem(
                            file_id=uuid.UUID(str(att.get("file_id"))),
                            file_name=str(att.get("file_name") or "attachment"),
                            size=int(att.get("size") or 0),
                            content_type=att.get("content_type"),
                            uploaded_by=_as_uuid(att.get("uploaded_by")),
                            uploaded_by_name=att.get("uploaded_by_name"),
                            uploaded_at=_as_datetime(att.get("uploaded_at")),
                        )
                        for att in (entry.get("attachments") or [])
                        if isinstance(att, dict) and _is_uuid(att.get("file_id"))
                    ],
                    author_id=_as_uuid(entry.get("author_id")),
                    author_name=entry.get("author_name") or names.get(str(entry.get("author_id"))),
                    author_avatar=_avatar_of(profiles, entry.get("author_id")),
                    create_time=_as_datetime(entry.get("create_time")),
                )
                for entry in (row.investigation_records or [])
                if isinstance(entry, dict)
            ],
            review_opinions=[
                ReviewOpinionItem(
                    step=str(entry.get("step") or ""),
                    step_label=entry.get("step_label") or _step_label(entry.get("step")),
                    result=str(entry.get("result") or ""),
                    author_id=_as_uuid(entry.get("author_id")),
                    author_name=entry.get("author_name"),
                    author_avatar=_avatar_of(profiles, entry.get("author_id")),
                    content=str(entry.get("content") or ""),
                    create_time=_as_datetime(entry.get("create_time")),
                )
                for entry in (row.review_opinions or [])
            ],
            report_content=row.report_content,
            report_versions=[
                ReportVersionItem(
                    content=str(entry.get("content") or ""),
                    editor_id=_as_uuid(entry.get("editor_id")),
                    editor_name=entry.get("editor_name") or names.get(str(entry.get("editor_id"))),
                    editor_avatar=_avatar_of(profiles, entry.get("editor_id")),
                    edit_time=_as_datetime(entry.get("edit_time")),
                    change_summary=entry.get("change_summary"),
                )
                for entry in (row.report_versions or [])
            ],
            steps=step_models,
            current_step=current_step,
            current_step_label=_step_label(current_step),
            status_updated_at=row.status_updated_at,
            can_operate=bool(actions),
            allowed_actions=actions,
            editable=editable,
            can_edit_investigation=can_edit_investigation,
            can_edit_cross_dept=can_edit_cross_dept,
        )

    @staticmethod
    def _build_cross_dept_item(
        entry: dict[str, Any],
        flow: FlowContext,
        names: dict[str, str],
        row: DeviationLedger,
        viewer_id: uuid.UUID | None,
        viewer_is_superuser: bool,
    ) -> CrossDeptReviewerItem:
        """跨部门行输出：审核人解析（空行回退部门负责人）+ 行状态 + 查看人可审批标记。"""
        reviewer_ids = cross_dept_row_reviewer_ids(entry, flow.contacts, flow.directory)
        approved = is_cross_dept_row_approved(entry)
        return CrossDeptReviewerItem(
            department=str(entry.get("department") or ""),
            investigator_ids=[uuid.UUID(token) for token in (entry.get("investigator_ids") or []) if _is_uuid(token)],
            investigator_names=[names.get(str(token), "-") for token in (entry.get("investigator_ids") or [])],
            reviewer_names=[flow.directory.name(uid) or "-" for uid in reviewer_ids],
            review_state=CROSS_DEPT_ROW_APPROVED if approved else CROSS_DEPT_ROW_PENDING,
            approved_by=_as_uuid(entry.get("approved_by")),
            approved_name=str(entry.get("approved_name") or "") or None,
            approved_at=_as_datetime(entry.get("approved_at")),
            opinion=str(entry.get("opinion") or "") or None,
            can_approve=bool(
                not approved
                and row.status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
                and viewer_id is not None
                and (viewer_is_superuser or viewer_id in set(reviewer_ids))
            ),
        )

    async def _load_user_profiles(
        self, row: DeviationLedger, extra_ids: Iterable[uuid.UUID]
    ) -> dict[str, _UserProfile]:
        ids: set[uuid.UUID] = set(extra_ids)
        ids.add(row.discoverer_id)
        ids.add(row.reporter_id)
        ids.update(row.handler_ids or [])
        if not ids:
            return {}
        result = await self.db.execute(
            select(User.id, User.name, User.avatar_thumb, User.avatar_url).where(User.id.in_(ids))
        )
        return {
            str(user_id): _UserProfile(id=user_id, name=name or "-", avatar_url=avatar_thumb or avatar_url)
            for user_id, name, avatar_thumb, avatar_url in result.all()
        }

    # ── 内部：列表组装 ────────────────────────────────────────────────

    def _resolve_handler(
        self,
        row: DeviationLedger,
        contacts: dict[str, Any],
        directory: HandlerDirectory,
    ) -> str | None:
        """按状态推导当前处理人：先按部门联系人解析，为空回落角色名。"""
        step = row.returned_step if row.status == LedgerStatus.RETURNED.value else STATUS_TO_STEP.get(row.status)
        if step:
            handlers = resolve_step_handlers(row, contacts, directory).get(step, [])
            names = [ref.name for ref in directory.refs(handlers)]
            if names:
                return "、".join(names)
        return constants.HANDLER_ROLE_LABELS.get(row.status)

    def _overdue(self, row: DeviationLedger, now: datetime) -> tuple[bool, int]:
        """超期判定：待办状态且 now - status_updated_at 超过环节阈值。"""
        threshold = constants.STEP_OVERDUE_DAYS.get(row.status)
        if threshold is None or not row.status.startswith("pending_") or row.status_updated_at is None:
            return False, 0
        updated = row.status_updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        elapsed_days = int((now - updated).total_seconds() // 86400)
        overdue_days = elapsed_days - threshold
        if overdue_days > 0:
            return True, overdue_days
        return False, 0

    def _to_item(
        self,
        row: DeviationLedger,
        names: dict[str, str],
        profiles: dict[str, _UserProfile],
        contacts: dict[str, Any],
        directory: HandlerDirectory,
        now: datetime,
    ) -> LedgerItem:
        is_overdue, overdue_days = self._overdue(row, now)
        handler_names = [names.get(str(handler_id), "-") for handler_id in (row.handler_ids or [])]
        return LedgerItem(
            id=row.id,
            code=row.code,
            final_code=row.final_code,
            display_code=row.final_code or row.code,
            title=row.title,
            department=row.department,
            discovery_date=row.discovery_date,
            status=row.status,
            status_label=constants.status_label(row.status),
            is_overdue=is_overdue,
            overdue_days=overdue_days,
            current_handler=self._resolve_handler(row, contacts, directory),
            current_handlers=self._current_handler_people(row, contacts, directory),
            deviation_level=row.deviation_level,
            level_label=constants.level_label(row.deviation_level),
            reporter_name=names.get(str(row.reporter_id)),
            reporter=_person(profiles, row.reporter_id),
            handler_names=handler_names,
            handlers=[
                person
                for person in (_person(profiles, handler_id) for handler_id in (row.handler_ids or []))
                if person is not None
            ],
            returned_step=row.returned_step,
            returned_step_label=_step_label(row.returned_step),
            created_at=row.created_at,
        )

    def _current_handler_people(
        self,
        row: DeviationLedger,
        contacts: dict[str, Any],
        directory: HandlerDirectory,
    ) -> list[StepHandlerPerson]:
        """当前处理人（含头像）：与 ``current_handler`` 同一解析口径。"""
        step = row.returned_step if row.status == LedgerStatus.RETURNED.value else STATUS_TO_STEP.get(row.status)
        if not step:
            return []
        refs = directory.refs(resolve_step_handlers(row, contacts, directory).get(step, []))
        return [StepHandlerPerson(id=ref.id, name=ref.name, avatar_url=ref.avatar_url) for ref in refs]

    # ── 内部：通知 ────────────────────────────────────────────────────

    def _name_of(self, outcome: TransitionOutcome, user_id: uuid.UUID) -> str:
        return outcome.directory.name(user_id) or "-"

    def _schedule_transition_notice(self, outcome: TransitionOutcome) -> None:
        """提交成功后异步发送流转通知（不阻塞接口、不影响事务）。"""
        ledger = outcome.ledger
        if outcome.result == REJECTED:
            recipients = outcome.refs_for(outcome.step) or outcome.directory.refs(list(ledger.handler_ids or []))
            reporter = outcome.directory.ref(ledger.reporter_id)
            if reporter is not None and all(ref.id != reporter.id for ref in recipients):
                recipients.append(reporter)
        else:
            recipients = outcome.next_handlers
        cross_recipients: list[HandlerRef] = []
        if outcome.next_status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value:
            cross_recipients = outcome.refs_for("cross_dept_head_review")
        # 待办角色/时限取自下一环节；退回时由上报人与调查人修改后重新提交
        next_step = STATUS_TO_STEP.get(outcome.next_status)
        if outcome.result == REJECTED:
            next_role_label = "上报人/调查人"
            deadline_days = None
        else:
            next_role_label = STEP_DEFS[next_step].role_label if next_step else ""
            deadline_days = constants.STEP_OVERDUE_DAYS.get(outcome.next_status)
        notice = notify.to_notice(ledger, reporter_name=self._name_of(outcome, ledger.reporter_id))
        notify.spawn(
            notify.notify_transition(
                notice,
                step_label=STEP_DEFS[outcome.step].label,
                result=outcome.result,
                content=outcome.content,
                actor_name=outcome.actor_name,
                next_status_label=constants.status_label(outcome.next_status),
                recipients=recipients,
                reporter=outcome.directory.ref(ledger.reporter_id),
                cross_recipients=cross_recipients,
                next_role_label=next_role_label,
                elapsed_hours=outcome.elapsed_hours,
                deadline_days=deadline_days,
            )
        )

    # ── 内部：权限 ────────────────────────────────────────────────────

    async def _current_review_step(self, ledger_id: uuid.UUID) -> str:
        row = await self.repo.get_by_id(ledger_id)
        if row is None:
            raise NotFoundException("偏差记录不存在")
        if row.status == LedgerStatus.RETURNED.value:
            return row.returned_step or ""
        return STATUS_TO_STEP.get(row.status, "")

    def _can_edit_analysis(
        self,
        row: DeviationLedger,
        actor_id: uuid.UUID,
        actor_is_superuser: bool,
    ) -> bool:
        """AI 分析结论的编辑范围与调查记录一致：上报人与调查人，超管放行。"""
        if actor_is_superuser or actor_id == row.reporter_id:
            return True
        return actor_id in set(row.handler_ids or [])

    def _assert_can_edit_investigation(
        self,
        row: DeviationLedger,
        actor_id: uuid.UUID,
        *,
        actor_is_superuser: bool = False,
    ) -> None:
        """调查记录 / 调查文档的编辑校验：待 AI 分析、调查中与审核阶段均允许，限调查人与上报人。"""
        step = row.returned_step if row.status == LedgerStatus.RETURNED.value else STATUS_TO_STEP.get(row.status)
        if step not in _INVESTIGATION_DOC_STEPS and not actor_is_superuser:
            raise BadRequestException("当前状态不允许编辑调查记录与调查文档")
        actors = set(row.handler_ids or []) | {row.reporter_id}
        if not actor_is_superuser and actor_id not in actors:
            raise ForbiddenException("只有调查人可以编辑调查记录与调查文档")


# ── 模块级辅助 ────────────────────────────────────────────────────────


def _allowed_actions(
    row: DeviationLedger,
    current_step: str | None,
    flow: FlowContext,
    *,
    viewer_id: uuid.UUID | None,
    viewer_is_superuser: bool,
) -> list[str]:
    """按状态 + 当前处理人计算可执行动作，前端据此显示按钮。"""
    if viewer_id is None:
        return []
    status = row.status
    handler_ids = set(flow.handlers.get(current_step or "", []))
    is_handler = viewer_is_superuser or (viewer_id in handler_ids if handler_ids else False)
    is_reporter = viewer_id == row.reporter_id
    is_investigator = viewer_id in set(row.handler_ids or [])

    can_edit_analysis = viewer_is_superuser or is_reporter or is_investigator
    if status == LedgerStatus.PENDING_AI_ANALYSIS.value:
        #: 分析只保存不流转，调查报告的提交才是流程推进入口，故此处同时放行调查
        return ["analyze", "investigate"] if can_edit_analysis else []
    if status == LedgerStatus.RETURNED.value:
        if not can_edit_analysis:
            return []
        #: 退回后既要重新提交，也要允许重新分析并保存结论
        return ["resubmit", "edit", "analyze"]
    if status == LedgerStatus.PENDING_INVESTIGATION.value:
        return ["investigate"] if is_handler or is_investigator else []
    if status == LedgerStatus.PENDING_FINAL_CODE.value:
        return ["final_code"] if is_handler else []
    if current_step in _REVIEW_STEPS and is_handler:
        definition = STEP_DEFS[current_step]
        #: 跨部门环节改由逐行审批（cross_dept_reviewers[].can_approve），整环节只保留退回
        actions = [] if current_step == CROSS_DEPT_STEP else ["approve"]
        if definition.allow_reject:
            actions.append("reject")
        if "deviation_level" in definition.requires:
            actions.append("grade")
        if "reason_category" in definition.requires:
            actions.append("reason_category")
        return actions
    return []


def _collect_detail_user_ids(
    row: DeviationLedger,
) -> tuple[set[uuid.UUID], set[uuid.UUID], set[uuid.UUID], set[uuid.UUID]]:
    """收集详情里出现的所有用户 ID，供一次查询解析姓名。"""
    opinion_ids = {
        uuid_value for entry in (row.review_opinions or []) if (uuid_value := _as_uuid(entry.get("author_id")))
    }
    investigation_ids = {
        uuid_value for entry in (row.investigation_records or []) if (uuid_value := _as_uuid(entry.get("author_id")))
    }
    uploader_ids = {
        uuid_value for entry in (row.attachments or []) if (uuid_value := _as_uuid(entry.get("uploaded_by")))
    }
    version_ids = {
        uuid_value for entry in (row.report_versions or []) if (uuid_value := _as_uuid(entry.get("editor_id")))
    }
    for entry in row.cross_dept_reviewers or []:
        for token in entry.get("investigator_ids") or []:
            parsed = _as_uuid(token)
            if parsed is not None:
                uploader_ids.add(parsed)
    return opinion_ids, investigation_ids, uploader_ids, version_ids


def _build_ai_messages(row: DeviationLedger) -> list[dict[str, Any]]:
    """构造 AI 结构化分析提示词，输出四个固定字段。"""
    system = (
        "你是制药企业GMP质量管理专家，负责偏差结构化分析。"
        "请严格输出 JSON 对象，包含 description（偏差描述）、reason（可能原因分析）、"
        "risk_assessment（风险评估）、capa_suggestion（CAPA建议）四个字段，使用简体中文，"
        "内容具体、可执行，不要输出多余字段。"
    )
    user = (
        f"偏差标题：{row.title}\n"
        f"发生部门：{row.department}\n"
        f"发现日期：{row.discovery_date}\n"
        f"发现地点：{row.discovery_location}\n"
        f"涉及物料/批次：{row.affected_items} / {row.batch_number}\n"
        f"偏差描述：{row.description}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _step_label(step: str | None) -> str | None:
    if not step:
        return None
    definition = STEP_DEFS.get(step)
    return definition.label if definition else constants.status_label(step)


class _UserProfile(NamedTuple):
    """用户展示信息：姓名 + 头像（飞书缩略图优先）。"""

    id: uuid.UUID
    name: str
    avatar_url: str | None = None


def _person(profiles: dict[str, _UserProfile], user_id: uuid.UUID | None) -> StepHandlerPerson | None:
    """从档案映射取「头像 + 姓名」；无对应档案返回 None（前端不渲染空占位）。"""
    if user_id is None:
        return None
    profile = profiles.get(str(user_id))
    if profile is None:
        return None
    return StepHandlerPerson(id=profile.id, name=profile.name, avatar_url=profile.avatar_url)


def _avatar_of(profiles: dict[str, _UserProfile], user_id: Any) -> str | None:
    if not user_id:
        return None
    profile = profiles.get(str(user_id))
    return profile.avatar_url if profile else None


def _preview_cache_key(ledger_id: uuid.UUID, file_id: uuid.UUID) -> str:
    """``.doc`` 转换结果的缓存 key，按台账 + 附件隔离。"""
    return f"deviation-ledger/{ledger_id}/.preview/{file_id}.docx"


def _docx_file_name(file_name: str) -> str:
    """``.doc`` 转换后对外展示的文件名（保留原名，仅换扩展名）。"""
    stem = os.path.splitext(file_name)[0] or "attachment"
    return f"{stem}.docx"


def _is_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return False
    return True


def _as_uuid(value: Any) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


__all__ = ["DeviationLedgerService"]
