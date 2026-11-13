"""偏差台账流程内核：状态↔环节映射、处理人解析、统一流转入口。

设计取舍：业务是固定 SOP 的串行 12 态，不引入流程引擎、不建流程配置中心。
所有环节定义收敛在这张 ``STEP_DEFS`` 表里，流转只走 ``transition()`` 一个入口；
将来若要配置化，只需把 StepDef 换成表驱动，``transition()`` 是唯一改动点。

处理人全部来自 ``quality.department_contacts``：

- 调查人：台账 ``handler_ids``
- 部门负责人：本部门 ``dept_head_id``
- 跨部门审核：按 ``cross_dept_reviewers`` 每行（部门 + 行内 ``investigator_ids`` + 行内 ``dept_head_id``）
  各生成「调查 → 审核」两个节点：行内调查人提交调查记录（服务层 ``submit_cross_dept_investigation``），
  行内部门负责人审批（``approve_cross_dept_row``）；行审核人优先取行内 ``dept_head_id``、
  缺省回退该部门 ``dept_head_id``；全部行通过后环节才前进，整环节驳回仍走 ``transition``
- 所属 QA：本部门 ``qa_reviewer_id``，缺则回退 ``qa_staff_ids[0]``
- QA 负责人：本部门 ``qa_head_id``（配置了就用本部门），缺则回退质量保证部 ``qa_head_id``，
  再缺则依次回退两行的 ``qa_staff_ids[1]`` 与质量保证部 ``dept_head_id``
- 质量负责人：本部门 ``quality_head_id``（配置了就用本部门），缺则回退质量保证部 ``quality_head_id``，
  再缺则取质量保证部 ``dept_head_id``
- 最终编号：本部门所属 QA
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.platform.audit.service import record_audit_log
from app.platform.identity.models import User

from . import deviation_ledger_constants as constants
from .deviation_department_models import DepartmentContact
from .deviation_ledger_constants import (
    CROSS_DEPT_INVESTIGATION_PENDING,
    CROSS_DEPT_INVESTIGATION_SUBMITTED,
    LedgerStatus,
)
from .deviation_ledger_models import DeviationLedger
from .deviation_ledger_repository import DeviationLedgerRepository

#: 质量保证部（QA 负责人 / 质量负责人所在部门）
QA_DEPARTMENT = "质量保证部"

APPROVED = "approved"
REJECTED = "rejected"
RESUBMITTED = "resubmitted"

#: 无处理人时允许自动跳过的环节（与妙搭一致：QA / QA 负责人）
_AUTO_SKIP_STATUSES: tuple[str, ...] = (
    LedgerStatus.PENDING_QA_REVIEW.value,
    LedgerStatus.PENDING_QA_HEAD_REVIEW.value,
)

#: 跨部门审核环节（未开启跨部门审核时步骤条标注为不适用，但不隐藏）
CROSS_DEPT_STEP = "cross_dept_head_review"
CROSS_DEPT_INAPPLICABLE_REASON = "本单未勾选跨部门审核，本环节不适用"
#: 跨部门单行的审核状态（存于 ``cross_dept_reviewers`` 行的 ``review_state`` 字段）
CROSS_DEPT_ROW_PENDING = "pending"
CROSS_DEPT_ROW_APPROVED = "approved"

#: 管理员代审：原因最少字数（挡住「1」「ok」这类无意义理由）与上限
OVERRIDE_REASON_MIN_LEN = 4
OVERRIDE_REASON_MAX_LEN = 200
#: 管理员代审的审计动作名（``audit.logs.action``）
OVERRIDE_AUDIT_ACTION = "deviation.superuser_override"


@dataclass(frozen=True, slots=True)
class StepDef:
    """一个流程环节的定义。"""

    step: str
    status: str
    label: str
    role_label: str
    permission: str
    requires: tuple[str, ...] = ()
    allow_reject: bool = True


STEP_DEFS: dict[str, StepDef] = {
    "ai_analysis": StepDef(
        step="ai_analysis",
        status=LedgerStatus.PENDING_AI_ANALYSIS.value,
        label="AI 智能分析",
        role_label="系统AI分析",
        permission="quality:deviation:update",
        allow_reject=False,
    ),
    "investigation": StepDef(
        step="investigation",
        status=LedgerStatus.PENDING_INVESTIGATION.value,
        label="偏差调查",
        role_label="调查人",
        permission="quality:deviation:submit",
        allow_reject=False,
    ),
    "dept_head_review": StepDef(
        step="dept_head_review",
        status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value,
        label="部门负责人审核",
        role_label="部门负责人",
        permission="quality:deviation:approve",
    ),
    "cross_dept_head_review": StepDef(
        step="cross_dept_head_review",
        status=LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        label="跨部门负责人审核",
        role_label="跨部门负责人",
        permission="quality:deviation:approve",
    ),
    "qa_review": StepDef(
        step="qa_review",
        status=LedgerStatus.PENDING_QA_REVIEW.value,
        label="所属QA审核",
        role_label="所属QA",
        permission="quality:deviation:approve",
        requires=("reason_category",),
    ),
    "qa_head_review": StepDef(
        step="qa_head_review",
        status=LedgerStatus.PENDING_QA_HEAD_REVIEW.value,
        label="QA负责人审核",
        role_label="QA负责人",
        permission="quality:deviation:approve",
        requires=("deviation_level",),
    ),
    "quality_head_review": StepDef(
        step="quality_head_review",
        status=LedgerStatus.PENDING_QUALITY_HEAD_REVIEW.value,
        label="质量负责人审核",
        role_label="质量负责人",
        permission="quality:deviation:approve",
    ),
    "final_code_input": StepDef(
        step="final_code_input",
        status=LedgerStatus.PENDING_FINAL_CODE.value,
        label="输入最终编号",
        role_label="所属QA",
        permission="quality:deviation:update",
        allow_reject=False,
    ),
}

#: 环节顺序（步骤条展示顺序）
STEP_ORDER: tuple[str, ...] = tuple(STEP_DEFS)

STATUS_TO_STEP: dict[str, str] = {definition.status: definition.step for definition in STEP_DEFS.values()}
STEP_TO_STATUS: dict[str, str] = {definition.step: definition.status for definition in STEP_DEFS.values()}


@dataclass(frozen=True, slots=True)
class HandlerRef:
    """处理人视图对象（含飞书标识，供通知使用；avatar_url 供前端头像展示）。

    ``feishu_open_id`` 是发消息的首选标识（``identity.users.feishu_open_id``，
    SSO 登录即可写入，无需 ``contact:user.employee_id:readonly`` 权限）；
    ``feishu_user_id`` 仅作历史兼容回退。
    """

    id: uuid.UUID
    name: str
    feishu_open_id: str | None = None
    feishu_user_id: str | None = None
    avatar_url: str | None = None

    @property
    def feishu_id(self) -> str | None:
        """可用的飞书标识（open_id 优先）。"""
        return self.feishu_open_id or self.feishu_user_id

    @property
    def feishu_id_type(self) -> str:
        """``feishu_id`` 对应的 ``receive_id_type``。"""
        return "open_id" if self.feishu_open_id else "user_id"


class HandlerDirectory:
    """一次请求内的处理人索引：UUID 与飞书标识（open_id / 历史 user_id）双向解析。"""

    def __init__(self, users: Mapping[uuid.UUID, HandlerRef]) -> None:
        self._by_id: dict[uuid.UUID, HandlerRef] = dict(users)
        self._by_feishu: dict[str, HandlerRef] = {}
        for ref in users.values():
            for token in (ref.feishu_open_id, ref.feishu_user_id):
                if token:
                    self._by_feishu.setdefault(token, ref)

    @classmethod
    async def load(
        cls,
        db: AsyncSession,
        ledger: DeviationLedger,
        contacts: Mapping[str, DepartmentContact],
        extra_ids: Iterable[uuid.UUID] = (),
    ) -> HandlerDirectory:
        """一次查询解析全部相关用户（联系人里的 UUID / open_id 混存都要兼容）。"""
        uuid_ids: set[uuid.UUID] = set(ledger.handler_ids or [])
        uuid_ids.add(ledger.reporter_id)
        uuid_ids.update(extra_ids)
        for entry in ledger.cross_dept_reviewers or []:
            for token in entry.get("investigator_ids") or []:
                if isinstance(token, uuid.UUID):
                    uuid_ids.add(token)
        return await cls.load_for_ids(db, contacts, uuid_ids, ledger.cross_dept_reviewers or [])

    @classmethod
    async def load_for_ids(
        cls,
        db: AsyncSession,
        contacts: Mapping[str, DepartmentContact],
        uuid_ids: Iterable[uuid.UUID] = (),
        cross_reviewers: Iterable[Mapping[str, Any]] = (),
    ) -> HandlerDirectory:
        """按联系人 + 指定用户 ID 批量加载，列表页多行共用一次查询。"""
        resolved_ids: set[uuid.UUID] = set(uuid_ids)
        text_ids: set[str] = set()
        for contact in contacts.values():
            for field_value in (
                contact.dept_head_id,
                contact.production_head_id,
                contact.quality_head_id,
                contact.qa_reviewer_id,
                contact.qa_head_id,
            ):
                if field_value is not None:
                    resolved_ids.add(field_value)
            for field_name in ("qa_staff_ids", "gmp_staff_ids", "additional_contacts"):
                for token in getattr(contact, field_name) or []:
                    # 配置页保存的是用户 UUID（与 dept_head_id 一致），历史数据可能是飞书 open_id，两者都要能查
                    cls._collect_token(token, resolved_ids, text_ids)
        for entry in cross_reviewers:
            for token in entry.get("investigator_ids") or []:
                cls._collect_token(token, resolved_ids, text_ids)
            #: 行内部门负责人也要能解析姓名（审核人展示与权限判断都依赖 directory）
            if entry.get("dept_head_id"):
                cls._collect_token(entry.get("dept_head_id"), resolved_ids, text_ids)

        conditions = []
        if resolved_ids:
            conditions.append(User.id.in_(resolved_ids))
        if text_ids:
            # 联系人的历史文本 token 可能是 open_id，也可能落在 feishu_user_id，两边都查
            conditions.append(User.feishu_open_id.in_(text_ids))
            conditions.append(User.feishu_user_id.in_(text_ids))
        if not conditions:
            return cls({})

        rows = await db.execute(
            select(
                User.id,
                User.name,
                User.feishu_open_id,
                User.feishu_user_id,
                User.avatar_thumb,
                User.avatar_url,
            ).where(
                User.is_deleted.is_(False),  # noqa: E712
                or_(*conditions),
            )
        )
        users = {
            row.id: HandlerRef(
                id=row.id,
                name=row.name or "-",
                feishu_open_id=row.feishu_open_id,
                feishu_user_id=row.feishu_user_id,
                avatar_url=row.avatar_thumb or row.avatar_url,
            )
            for row in rows.all()
        }
        return cls(users)

    @staticmethod
    def _collect_token(
        token: str | uuid.UUID | None,
        resolved_ids: set[uuid.UUID],
        text_ids: set[str],
    ) -> None:
        """UUID 字符串按主键查，其它 token（飞书 open_id）按飞书标识字段查。"""
        if isinstance(token, uuid.UUID):
            resolved_ids.add(token)
            return
        cleaned = str(token or "").strip()
        if not cleaned:
            return
        try:
            resolved_ids.add(uuid.UUID(cleaned))
        except ValueError:
            text_ids.add(cleaned)

    def resolve(self, tokens: Sequence[str | uuid.UUID] | None) -> list[uuid.UUID]:
        """把 UUID / open_id / 字符串 UUID 统一解析成用户 ID，解析不出的丢弃。"""
        resolved: list[uuid.UUID] = []
        for token in tokens or []:
            ref = self._lookup(token)
            if ref is not None and ref.id not in resolved:
                resolved.append(ref.id)
        return resolved

    def ref(self, user_id: uuid.UUID) -> HandlerRef | None:
        return self._by_id.get(user_id)

    def name(self, user_id: uuid.UUID) -> str | None:
        ref = self._by_id.get(user_id)
        return ref.name if ref else None

    def refs(self, user_ids: Sequence[uuid.UUID]) -> list[HandlerRef]:
        return [ref for ref in (self._by_id.get(user_id) for user_id in user_ids) if ref is not None]

    def all_refs(self) -> list[HandlerRef]:
        """索引中的全部用户（列表页一次查询后复用）。"""
        return list(self._by_id.values())

    def _lookup(self, token: str | uuid.UUID) -> HandlerRef | None:
        if isinstance(token, uuid.UUID):
            return self._by_id.get(token)
        cleaned = str(token).strip()
        if not cleaned:
            return None
        try:
            parsed = uuid.UUID(cleaned)
        except ValueError:
            return self._by_feishu.get(cleaned)
        return self._by_id.get(parsed)


@dataclass(slots=True)
class FlowContext:
    """一次流转所需上下文：联系人、处理人索引、各环节处理人。"""

    contacts: dict[str, DepartmentContact]
    directory: HandlerDirectory
    handlers: dict[str, list[uuid.UUID]]

    def refs(self, step: str) -> list[HandlerRef]:
        return self.directory.refs(self.handlers.get(step, []))

    def handler_names(self, step: str) -> str | None:
        names = [ref.name for ref in self.refs(step)]
        return "、".join(names) if names else None


@dataclass(slots=True)
class TransitionOutcome:
    """流转结果，供 API 组装响应与异步通知。"""

    ledger: DeviationLedger
    step: str
    result: str
    previous_status: str
    next_status: str
    skipped_steps: list[str]
    next_handlers: list[HandlerRef]
    actor_name: str
    directory: HandlerDirectory
    handlers: dict[str, list[uuid.UUID]]
    #: 本次操作填写的意见（退回理由 / 审核意见 / 调查结论），供通知摘要使用
    content: str = ""
    #: 上一环节已停留小时数（流转前的 ``status_updated_at`` 至今），用于提示处理时效
    elapsed_hours: float | None = None

    def refs_for(self, step: str) -> list[HandlerRef]:
        """指定环节的处理人（通知退回 / 跨部门指派时使用）。"""
        return self.directory.refs(self.handlers.get(step, []))


async def load_contacts(db: AsyncSession) -> dict[str, DepartmentContact]:
    """读取全部启用中的部门联系人，按部门名索引。"""
    rows = await db.execute(
        select(DepartmentContact).where(DepartmentContact.is_deleted.is_(False))  # noqa: E712
    )
    return {row.department: row for row in rows.scalars().all() if row.department}


async def build_flow_context(db: AsyncSession, ledger: DeviationLedger) -> FlowContext:
    """组装流程上下文（详情页、流转、通知共用）。"""
    contacts = await load_contacts(db)
    directory = await HandlerDirectory.load(db, ledger, contacts)
    handlers = resolve_step_handlers(ledger, contacts, directory)
    return FlowContext(contacts=contacts, directory=directory, handlers=handlers)


def _own_qa_reviewer_ids(contact: DepartmentContact, directory: HandlerDirectory) -> list[uuid.UUID]:
    """所属 QA：新列优先，历史数组 ``[0]`` 兜底（兼容导入脚本只写数组的情况）。"""
    if contact.qa_reviewer_id is not None:
        return [contact.qa_reviewer_id]
    return directory.resolve((contact.qa_staff_ids or [])[:1])


def _qa_head_ids(
    own: DepartmentContact | None,
    qa_dept: DepartmentContact | None,
    directory: HandlerDirectory,
) -> list[uuid.UUID]:
    """QA 负责人：本部门配置优先（配置了就该生效），缺则回退质量保证部。

    每行内部仍按「新列 → 历史数组 ``[1]``」兜底，两行都没有则取质量保证部部门负责人。
    """
    for contact in (own, qa_dept):
        if contact is None:
            continue
        if contact.qa_head_id is not None:
            return [contact.qa_head_id]
        qa_staff = list(contact.qa_staff_ids or [])
        resolved = directory.resolve(qa_staff[1:2]) if len(qa_staff) > 1 else []
        if resolved:
            return resolved
    return [qa_dept.dept_head_id] if qa_dept is not None and qa_dept.dept_head_id is not None else []


def _quality_head_ids(
    own: DepartmentContact | None,
    qa_dept: DepartmentContact | None,
) -> list[uuid.UUID]:
    """质量负责人：本部门配置优先（配置了就该生效），缺则回退质量保证部。"""
    for contact in (own, qa_dept):
        if contact is not None and contact.quality_head_id is not None:
            return [contact.quality_head_id]
    return [qa_dept.dept_head_id] if qa_dept is not None and qa_dept.dept_head_id is not None else []


def resolve_step_handlers(
    ledger: DeviationLedger,
    contacts: Mapping[str, DepartmentContact],
    directory: HandlerDirectory,
) -> dict[str, list[uuid.UUID]]:
    """按部门联系人表解析每个环节的处理人；解析不出即为空列表。"""
    handlers: dict[str, list[uuid.UUID]] = {step: [] for step in STEP_ORDER}
    own = contacts.get((ledger.department or "").strip())
    qa_dept = contacts.get(QA_DEPARTMENT)

    handlers["investigation"] = list(ledger.handler_ids or [])

    if own is not None:
        if own.dept_head_id is not None:
            handlers["dept_head_review"] = [own.dept_head_id]
        handlers["qa_review"] = _own_qa_reviewer_ids(own, directory)

    cross_ids: list[uuid.UUID] = []
    for entry in ledger.cross_dept_reviewers or []:
        if not isinstance(entry, dict):
            continue
        for reviewer_id in cross_dept_row_reviewer_ids(entry, contacts, directory):
            if reviewer_id not in cross_ids:
                cross_ids.append(reviewer_id)
    handlers["cross_dept_head_review"] = cross_ids

    handlers["qa_head_review"] = _qa_head_ids(own, qa_dept, directory)
    handlers["quality_head_review"] = _quality_head_ids(own, qa_dept)

    handlers["final_code_input"] = list(handlers["qa_review"])
    # AI 分析环节由具备编辑权限的人操作，不锁定处理人
    handlers["ai_analysis"] = []
    return handlers


def needs_cross_dept_review(ledger: DeviationLedger) -> bool:
    """本单是否真的会经过跨部门负责人审核（开关开启且填了跨部门部门）。"""
    return bool(ledger.needs_cross_dept_review and ledger.cross_dept_reviewers)


def cross_dept_review_rows(ledger: DeviationLedger) -> list[dict[str, Any]]:
    """台账跨部门行（过滤非 dict 脏数据，保持原顺序）。"""
    return [entry for entry in (ledger.cross_dept_reviewers or []) if isinstance(entry, dict)]


def cross_dept_row_reviewer_ids(
    entry: Mapping[str, Any],
    contacts: Mapping[str, DepartmentContact],
    directory: HandlerDirectory,
) -> list[uuid.UUID]:
    """单行跨部门的审核人：行内显式部门负责人优先，缺省回退该部门联系人配置的负责人。"""
    head_id = entry.get("dept_head_id")
    if head_id:
        resolved = directory.resolve([head_id])
        if resolved:
            return resolved
    department = str(entry.get("department") or "").strip()
    contact = contacts.get(department)
    if contact is not None and contact.dept_head_id is not None:
        return [contact.dept_head_id]
    return []


def cross_dept_row_investigator_ids(entry: Mapping[str, Any], directory: HandlerDirectory) -> list[uuid.UUID]:
    """单行跨部门的调查人（行内 ``investigator_ids``，供「调查」节点权限判断）。"""
    return directory.resolve(entry.get("investigator_ids") or [])


def cross_dept_row_requires_investigation(entry: Mapping[str, Any]) -> bool:
    """单行是否需要「调查」节点：配置了行内调查人才需要，未配置时负责人直接审核。"""
    return bool(entry.get("investigator_ids"))


def is_cross_dept_row_investigated(entry: Mapping[str, Any]) -> bool:
    """单行调查是否已提交。"""
    return str(entry.get("investigate_state") or "") == CROSS_DEPT_INVESTIGATION_SUBMITTED


def is_cross_dept_row_approved(entry: Mapping[str, Any]) -> bool:
    """单行是否已审核通过。"""
    return str(entry.get("review_state") or "") == CROSS_DEPT_ROW_APPROVED


def all_cross_dept_rows_approved(ledger: DeviationLedger) -> bool:
    """全部跨部门行是否都已通过（无行视为未配置、不通过）。"""
    rows = cross_dept_review_rows(ledger)
    return bool(rows) and all(is_cross_dept_row_approved(entry) for entry in rows)


def reset_cross_dept_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    """整环节退回后重置全部跨部门行：审核状态与审批痕迹清空，行调查结果保留。

    JSONB 必须整体重新赋值，故返回新列表（调用方赋回 ``cross_dept_reviewers``）。
    """
    return [
        {
            **entry,
            "review_state": CROSS_DEPT_ROW_PENDING,
            "approved_by": None,
            "approved_name": None,
            "approved_at": None,
            "opinion": None,
        }
        for entry in rows
        if isinstance(entry, dict)
    ]


#: 不能作为退回目标的环节：AI 分析由系统完成，最终编号是收尾动作，均非人工重做点
_NON_RETURNABLE_STEPS: frozenset[str] = frozenset({"ai_analysis", "final_code_input"})


def returnable_steps(
    ledger: DeviationLedger,
    current_step: str,
    handlers: Mapping[str, list[uuid.UUID]],
) -> list[str]:
    """可退回的前置环节，按流程顺序排列（最近的在最后）。

    只保留当前环节之前、本单实际适用、且能解析到处理人的人工环节；
    跨部门未开启时不会把跨部门环节列为目标，无处理人的环节也无法承接退回。
    """
    if current_step not in STEP_ORDER:
        return []
    current_index = STEP_ORDER.index(current_step)
    candidates: list[str] = []
    for step in STEP_ORDER[:current_index]:
        if step in _NON_RETURNABLE_STEPS:
            continue
        applicable, _, _ = step_note(ledger, step)
        if not applicable or not handlers.get(step):
            continue
        candidates.append(step)
    return candidates


def cross_dept_row_payloads(
    ledger: DeviationLedger,
    contacts: Mapping[str, DepartmentContact],
    directory: HandlerDirectory,
) -> list[dict[str, Any]]:
    """跨部门逐行审核节点展示数据（流转图 sub_items 与详情行共用）。"""
    rows: list[dict[str, Any]] = []
    for entry in cross_dept_review_rows(ledger):
        department = str(entry.get("department") or "").strip()
        reviewer_ids = cross_dept_row_reviewer_ids(entry, contacts, directory)
        rows.append(
            {
                "department": department,
                "reviewer_names": [directory.name(uid) for uid in reviewer_ids],
                "investigate_state": (
                    CROSS_DEPT_INVESTIGATION_SUBMITTED
                    if is_cross_dept_row_investigated(entry)
                    else CROSS_DEPT_INVESTIGATION_PENDING
                ),
                "state": CROSS_DEPT_ROW_APPROVED if is_cross_dept_row_approved(entry) else CROSS_DEPT_ROW_PENDING,
                "approved_by_name": str(entry.get("approved_name") or "") or None,
                "approved_at": entry.get("approved_at"),
                "opinion": str(entry.get("opinion") or "") or None,
            }
        )
    return rows


def step_note(ledger: DeviationLedger, step: str) -> tuple[bool, str | None, bool]:
    """环节展示标注：(本单是否需要该环节, 不适用原因, 无处理人时是否自动跳过)。

    步骤条固定展示全部环节（GMP 可追溯），不参与的环节用标注说明，不隐藏。
    """
    if step == CROSS_DEPT_STEP and not needs_cross_dept_review(ledger):
        return False, CROSS_DEPT_INAPPLICABLE_REASON, False
    return True, None, STEP_DEFS[step].status in _AUTO_SKIP_STATUSES


def allowed_actors(ledger: DeviationLedger, step: str, handlers: Mapping[str, list[uuid.UUID]]) -> set[uuid.UUID]:
    """环节的可操作人集合（AI 分析 / 退回重提额外允许上报人与调查人）。"""
    allowed: set[uuid.UUID] = set(handlers.get(step, []))
    if step in ("ai_analysis", "final_code_input") or step == "investigation":
        allowed.add(ledger.reporter_id)
        allowed.update(ledger.handler_ids or [])
    return allowed


def resolve_override_reason(
    actor_id: uuid.UUID,
    allowed: set[uuid.UUID],
    *,
    actor_is_superuser: bool,
    override_reason: str | None,
) -> str | None:
    """超级管理员「代审」原因：超管不在处理人集合内时视为代审，必须填写原因。

    非超管、或超管本人恰好就是该环节处理人时返回 ``None``（不算代审）。
    代审原因会写进审核意见并落平台审计日志，便于 GMP 抽查时区分「本人职责」与
    「管理员代操作」。
    """
    if not actor_is_superuser or actor_id in allowed:
        return None
    reason = (override_reason or "").strip()
    if len(reason) < OVERRIDE_REASON_MIN_LEN:
        raise BadRequestException(
            f"管理员代审必须填写代审原因（不少于 {OVERRIDE_REASON_MIN_LEN} 个字），将记入审计日志"
        )
    if len(reason) > OVERRIDE_REASON_MAX_LEN:
        raise BadRequestException(f"代审原因不能超过 {OVERRIDE_REASON_MAX_LEN} 个字")
    return reason


def ensure_actor_allowed(
    step: str,
    allowed: set[uuid.UUID],
    actor_id: uuid.UUID,
    *,
    actor_is_superuser: bool,
    override_reason: str | None = None,
) -> str | None:
    """校验操作人是否在该环节的可操作人集合内，返回代审原因（非代审返回 ``None``）。

    超级管理员保留兜底能力，但代审必须填写原因；其余人一律严格校验。环节未解析到
    任何处理人时直接拒绝并提示去配置，避免「没有负责人也能审核」。
    """
    if actor_is_superuser:
        return resolve_override_reason(
            actor_id, allowed, actor_is_superuser=True, override_reason=override_reason
        )
    role_label = STEP_DEFS[step].role_label
    if not allowed:
        raise ForbiddenException(f"当前环节（{role_label}）未配置处理人，请先在部门联系人配置中配置后再操作")
    if actor_id not in allowed:
        raise ForbiddenException(f"当前环节由{role_label}处理，你无权操作")
    return None


def format_opinion_content(content: str, override_reason: str | None) -> str:
    """审核意见正文：代审时加「【管理员代审】原因」前缀，便于人读与事后抽查。"""
    if not override_reason:
        return content
    return f"【管理员代审】{override_reason}｜{content}".rstrip("｜")


def _append_opinion(
    ledger: DeviationLedger,
    *,
    step: str,
    result: str,
    actor_id: uuid.UUID,
    actor_name: str,
    content: str,
    step_label: str | None = None,
    override_reason: str | None = None,
) -> None:
    body = format_opinion_content(content, override_reason)
    opinion = {
        "step": step,
        "step_label": step_label or STEP_DEFS[step].label,
        "result": result,
        "author_id": str(actor_id),
        "author_name": actor_name,
        "content": body,
        #: 超管代审标记：详情页与抽查脚本据此区分「本人职责」与「管理员代操作」
        "is_override": bool(override_reason),
        "override_reason": override_reason,
        "create_time": datetime.now(UTC).isoformat(),
    }
    ledger.review_opinions = [*(ledger.review_opinions or []), opinion]


async def record_override_audit(
    db: AsyncSession,
    *,
    ledger: DeviationLedger,
    step: str,
    result: str,
    actor_id: uuid.UUID,
    reason: str,
    department: str | None = None,
) -> None:
    """记录管理员代审审计日志（与业务变更同事务提交）。"""
    await record_audit_log(
        db,
        action=OVERRIDE_AUDIT_ACTION,
        user_id=actor_id,
        resource_type="quality.deviation_ledger",
        resource_id=ledger.id,
        new_value={
            "step": step,
            "result": result,
            "override_reason": reason,
            "department": department,
            "status": ledger.status,
            "code": ledger.code,
        },
        extra={"app_module": "quality"},
    )


def _next_status_on_approve(ledger: DeviationLedger, step: str) -> str:
    """通过后的目标状态（不含自动跳过）。"""
    if step == "ai_analysis":
        return LedgerStatus.PENDING_INVESTIGATION.value
    if step == "investigation":
        return LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value
    if step == "dept_head_review":
        return (
            LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
            if needs_cross_dept_review(ledger)
            else LedgerStatus.PENDING_QA_REVIEW.value
        )
    if step == "cross_dept_head_review":
        return LedgerStatus.PENDING_QA_REVIEW.value
    if step == "qa_review":
        return LedgerStatus.PENDING_QA_HEAD_REVIEW.value
    if step == "qa_head_review":
        return LedgerStatus.PENDING_QUALITY_HEAD_REVIEW.value
    if step == "quality_head_review":
        return LedgerStatus.PENDING_FINAL_CODE.value
    raise BadRequestException("该环节不支持通过操作")


def _apply_auto_skip(
    next_status: str,
    handlers: Mapping[str, list[uuid.UUID]],
) -> tuple[str, list[str]]:
    """无处理人的 QA / QA 负责人环节自动跳过，避免流程卡死。"""
    skipped: list[str] = []
    while next_status in _AUTO_SKIP_STATUSES:
        step = STATUS_TO_STEP[next_status]
        if handlers.get(step):
            break
        skipped.append(step)
        next_status = _next_status_on_approve_status(next_status)
    return next_status, skipped


def _next_status_on_approve_status(status: str) -> str:
    if status == LedgerStatus.PENDING_QA_REVIEW.value:
        return LedgerStatus.PENDING_QA_HEAD_REVIEW.value
    if status == LedgerStatus.PENDING_QA_HEAD_REVIEW.value:
        return LedgerStatus.PENDING_QUALITY_HEAD_REVIEW.value
    return status


def _advance_if_cross_dept_complete(
    ledger: DeviationLedger,
    next_status: str,
    handlers: Mapping[str, list[uuid.UUID]],
) -> tuple[str, list[str]]:
    """进入跨部门环节时若所有行已通过则继续前进，避免「无人可操作」的卡死。

    正常路径下退回会重置所有行，这里是防御性兜底（例如历史数据行状态残留）。
    """
    if next_status != LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value:
        return next_status, []
    if not all_cross_dept_rows_approved(ledger):
        return next_status, []
    following, auto_skipped = _apply_auto_skip(_next_status_on_approve(ledger, CROSS_DEPT_STEP), handlers)
    return following, [CROSS_DEPT_STEP, *auto_skipped]


def _elapsed_hours(start: datetime | None, now: datetime) -> float | None:
    """两个时间点之间的时长（小时）；``start`` 缺失或为 naive 时按 UTC 解释。"""
    if start is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return round(max((now - start).total_seconds(), 0.0) / 3600, 1)


async def transition(
    db: AsyncSession,
    *,
    ledger_id: uuid.UUID,
    step: str,
    result: str,
    content: str,
    actor_id: uuid.UUID,
    actor_name: str,
    actor_is_superuser: bool = False,
    target_step: str | None = None,
    reason_category: str | None = None,
    deviation_level: str | None = None,
    override_reason: str | None = None,
) -> TransitionOutcome:
    """统一流转入口：校验 → 守卫 → 追加意见 → 推进状态（含自动跳过）。

    ``target_step`` 只在 ``result == rejected`` 时生效：缺省退到最近的前置环节，
    显式传入时必须落在 ``returnable_steps()`` 内，防止伪造跳到未来环节。
    """
    if step not in STEP_DEFS:
        raise BadRequestException("未知的流程环节")
    if result not in (APPROVED, REJECTED, RESUBMITTED):
        raise BadRequestException("未知的审核结论")

    repo = DeviationLedgerRepository(db)
    ledger = await repo.get_by_id_for_update(ledger_id)
    if ledger is None:
        raise NotFoundException("偏差记录不存在")

    previous_status = ledger.status
    current_step = STATUS_TO_STEP.get(previous_status)
    if result == RESUBMITTED:
        if previous_status != LedgerStatus.RETURNED.value or ledger.returned_step != step:
            raise BadRequestException("当前状态不允许重新提交")
    elif current_step != step:
        raise BadRequestException(f"当前状态为「{constants.status_label(previous_status)}」，不能执行该操作")

    if result == REJECTED and not STEP_DEFS[step].allow_reject:
        raise BadRequestException("该环节不支持退回")
    if step == CROSS_DEPT_STEP and result == APPROVED:
        raise BadRequestException("跨部门审核请按部门逐行通过")

    context = await build_flow_context(db, ledger)

    if result == RESUBMITTED:
        # 退回后的重新提交由上报人 / 调查人发起（也可由被退回环节的处理人代提交）
        allowed = set(ledger.handler_ids or []) | {ledger.reporter_id}
        allowed.update(context.handlers.get(step, []))
    else:
        allowed = allowed_actors(ledger, step, context.handlers)
    override = ensure_actor_allowed(
        step, allowed, actor_id, actor_is_superuser=actor_is_superuser, override_reason=override_reason
    )

    if result == APPROVED:
        if "reason_category" in STEP_DEFS[step].requires:
            category = (reason_category or ledger.reason_category or "").strip()
            if not category:
                raise BadRequestException("请先选择原因分类")
            ledger.reason_category = category
        if "deviation_level" in STEP_DEFS[step].requires:
            level = (deviation_level or ledger.deviation_level or "").strip()
            if not level:
                raise BadRequestException("请先完成偏差分级")
            if level not in constants.DEVIATION_LEVELS:
                raise BadRequestException("偏差分级取值不合法")
            ledger.deviation_level = level

    #: 先算出目标状态（退回目标校验失败时不写入任何审核意见）
    skipped: list[str] = []
    return_target: str | None = None
    if result == REJECTED:
        candidates = returnable_steps(ledger, step, context.handlers)
        if not candidates:
            raise BadRequestException(f"「{STEP_DEFS[step].label}」没有可退回的前置环节")
        return_target = (target_step or "").strip() or candidates[-1]
        if return_target not in candidates:
            raise BadRequestException("退回目标环节不合法，请选择已完成的前置环节")
        next_status = STEP_TO_STATUS[return_target]
    elif result == RESUBMITTED:
        next_status = STEP_TO_STATUS[step]
    else:
        next_status = _next_status_on_approve(ledger, step)
        next_status, skipped = _apply_auto_skip(next_status, context.handlers)
        next_status, cross_skipped = _advance_if_cross_dept_complete(ledger, next_status, context.handlers)
        skipped.extend(cross_skipped)

    _append_opinion(
        ledger,
        step=step,
        result=result,
        actor_id=actor_id,
        actor_name=actor_name,
        content=content.strip(),
        override_reason=override,
    )

    if return_target is not None:
        ledger.returned_step = return_target
        #: 退回到跨部门环节及其之前时，所有部门行重置为待审核，避免「全部已通过却无人可操作」
        if needs_cross_dept_review(ledger) and STEP_ORDER.index(return_target) <= STEP_ORDER.index(CROSS_DEPT_STEP):
            ledger.cross_dept_reviewers = reset_cross_dept_rows(ledger.cross_dept_reviewers or [])
    elif result in (APPROVED, RESUBMITTED):
        #: 退回已消费：目标环节重新通过（或历史数据重新提交）后清空标记，列表不再展示「已退回」
        ledger.returned_step = None

    now = datetime.now(UTC)
    elapsed_hours = _elapsed_hours(ledger.status_updated_at, now)
    ledger.status = next_status
    ledger.status_updated_at = now
    ledger.updated_by = actor_id
    if override:
        await record_override_audit(
            db, ledger=ledger, step=step, result=result, actor_id=actor_id, reason=override
        )
    await db.commit()
    await db.refresh(ledger)

    return TransitionOutcome(
        ledger=ledger,
        step=step,
        result=result,
        previous_status=previous_status,
        next_status=next_status,
        skipped_steps=skipped,
        next_handlers=context.refs(STATUS_TO_STEP.get(next_status) or ""),
        actor_name=actor_name,
        directory=context.directory,
        handlers=context.handlers,
        content=content.strip(),
        elapsed_hours=elapsed_hours,
    )


async def approve_cross_dept_row(
    db: AsyncSession,
    *,
    ledger_id: uuid.UUID,
    department: str,
    content: str,
    actor_id: uuid.UUID,
    actor_name: str,
    actor_is_superuser: bool = False,
    override_reason: str | None = None,
) -> TransitionOutcome:
    """跨部门逐行审批：行审核人通过只写该行状态，全部行通过后环节才前进到所属 QA 审核。

    行审核人 = 行内显式部门负责人（缺省回退该部门联系人配置）；配置了行内调查人的行必须
    先提交调查（``investigate_state == submitted``）才可审批；重复审批同行直接拒绝（幂等保护）。
    """
    target_department = department.strip()
    if not target_department:
        raise BadRequestException("跨部门部门不能为空")

    repo = DeviationLedgerRepository(db)
    ledger = await repo.get_by_id_for_update(ledger_id)
    if ledger is None:
        raise NotFoundException("偏差记录不存在")
    if ledger.status != LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value:
        raise BadRequestException("当前状态不在跨部门审核环节，不能按部门审批")

    rows = cross_dept_review_rows(ledger)
    entry = next((item for item in rows if str(item.get("department") or "").strip() == target_department), None)
    if entry is None:
        raise NotFoundException("该跨部门行不存在")
    if is_cross_dept_row_approved(entry):
        raise BadRequestException("该部门已审核通过，无需重复审批")
    if cross_dept_row_requires_investigation(entry) and not is_cross_dept_row_investigated(entry):
        raise BadRequestException("该部门调查尚未提交，请等待调查人完成调查后再审核")

    context = await build_flow_context(db, ledger)
    reviewer_ids = cross_dept_row_reviewer_ids(entry, context.contacts, context.directory)
    if not reviewer_ids:
        raise BadRequestException("该跨部门行没有审核人，请在基础信息中补充该部门调查人或维护部门负责人")
    override = resolve_override_reason(
        actor_id, set(reviewer_ids), actor_is_superuser=actor_is_superuser, override_reason=override_reason
    )
    if not actor_is_superuser and actor_id not in reviewer_ids:
        raise ForbiddenException("只有该跨部门行的审核人可以审批")

    previous_status = ledger.status
    now = datetime.now(UTC)
    elapsed_hours = _elapsed_hours(ledger.status_updated_at, now)
    updated_rows: list[dict[str, Any]] = []
    for item in rows:
        if item is entry:
            updated_rows.append(
                {
                    **item,
                    "review_state": CROSS_DEPT_ROW_APPROVED,
                    "approved_by": str(actor_id),
                    "approved_name": actor_name,
                    "approved_at": now.isoformat(),
                    "opinion": content.strip(),
                }
            )
        else:
            updated_rows.append(dict(item))
    #: JSONB 原地修改不会被 SQLAlchemy 感知，必须整体重新赋值
    ledger.cross_dept_reviewers = updated_rows

    _append_opinion(
        ledger,
        step=CROSS_DEPT_STEP,
        result=APPROVED,
        actor_id=actor_id,
        actor_name=actor_name,
        content=content.strip(),
        step_label=f"{STEP_DEFS[CROSS_DEPT_STEP].label}（{target_department}）",
        override_reason=override,
    )
    ledger.updated_by = actor_id
    if override:
        await record_override_audit(
            db,
            ledger=ledger,
            step=CROSS_DEPT_STEP,
            result=APPROVED,
            actor_id=actor_id,
            reason=override,
            department=target_department,
        )

    skipped: list[str] = []
    if all(is_cross_dept_row_approved(item) for item in updated_rows):
        next_status = _next_status_on_approve(ledger, CROSS_DEPT_STEP)
        next_status, skipped = _apply_auto_skip(next_status, context.handlers)
        ledger.status = next_status
        ledger.status_updated_at = now
        #: 整环节退回后重新逐行通过：跨部门环节完成即视为退回已消费
        if ledger.returned_step == CROSS_DEPT_STEP:
            ledger.returned_step = None
    else:
        next_status = ledger.status

    await db.commit()
    await db.refresh(ledger)

    return TransitionOutcome(
        ledger=ledger,
        step=CROSS_DEPT_STEP,
        result=APPROVED,
        previous_status=previous_status,
        next_status=next_status,
        skipped_steps=skipped,
        next_handlers=context.refs(STATUS_TO_STEP.get(next_status) or ""),
        actor_name=actor_name,
        directory=context.directory,
        handlers=context.handlers,
        content=content.strip(),
        elapsed_hours=elapsed_hours if next_status != previous_status else None,
    )


async def reject_cross_dept_row(
    db: AsyncSession,
    *,
    ledger_id: uuid.UUID,
    department: str,
    content: str,
    actor_id: uuid.UUID,
    actor_name: str,
    actor_is_superuser: bool = False,
    override_reason: str | None = None,
) -> TransitionOutcome:
    """跨部门单行退回：只重置该部门的「调查 → 审核」两个节点，其余行已通过结果保留。

    台账仍停留在跨部门审核环节，由该部门调查人重做调查、部门负责人重新审核。
    """
    target_department = department.strip()
    if not target_department:
        raise BadRequestException("跨部门部门不能为空")
    reason = content.strip()
    if not reason:
        raise BadRequestException("退回时必须填写退回理由")

    repo = DeviationLedgerRepository(db)
    ledger = await repo.get_by_id_for_update(ledger_id)
    if ledger is None:
        raise NotFoundException("偏差记录不存在")
    if ledger.status != LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value:
        raise BadRequestException("当前状态不在跨部门审核环节，不能按部门退回")

    rows = cross_dept_review_rows(ledger)
    entry = next((item for item in rows if str(item.get("department") or "").strip() == target_department), None)
    if entry is None:
        raise NotFoundException("该跨部门行不存在")

    context = await build_flow_context(db, ledger)
    reviewer_ids = cross_dept_row_reviewer_ids(entry, context.contacts, context.directory)
    if not reviewer_ids:
        raise BadRequestException("该跨部门行没有审核人，请在基础信息中补充该部门调查人或维护部门负责人")
    override = resolve_override_reason(
        actor_id, set(reviewer_ids), actor_is_superuser=actor_is_superuser, override_reason=override_reason
    )
    if not actor_is_superuser and actor_id not in reviewer_ids:
        raise ForbiddenException("只有该跨部门行的审核人可以退回")

    previous_status = ledger.status
    now = datetime.now(UTC)
    elapsed_hours = _elapsed_hours(ledger.status_updated_at, now)
    requires_investigation = cross_dept_row_requires_investigation(entry)
    updated_rows: list[dict[str, Any]] = []
    for item in rows:
        if item is entry:
            reset: dict[str, Any] = {
                **item,
                "review_state": CROSS_DEPT_ROW_PENDING,
                "approved_by": None,
                "approved_name": None,
                "approved_at": None,
                "opinion": reason,
            }
            if requires_investigation:
                #: 只有配置了行内调查人的部门才需要重做调查，其余部门仅重做审核
                reset.update(
                    {
                        "investigate_state": CROSS_DEPT_INVESTIGATION_PENDING,
                        "investigate_submitted_by": None,
                        "investigate_submitted_name": None,
                        "investigate_submitted_at": None,
                    }
                )
            updated_rows.append(reset)
        else:
            updated_rows.append(dict(item))
    #: JSONB 原地修改不会被 SQLAlchemy 感知，必须整体重新赋值
    ledger.cross_dept_reviewers = updated_rows

    _append_opinion(
        ledger,
        step=CROSS_DEPT_STEP,
        result=REJECTED,
        actor_id=actor_id,
        actor_name=actor_name,
        content=reason,
        step_label=f"{STEP_DEFS[CROSS_DEPT_STEP].label}（{target_department}）",
        override_reason=override,
    )
    ledger.updated_by = actor_id
    if override:
        await record_override_audit(
            db,
            ledger=ledger,
            step=CROSS_DEPT_STEP,
            result=REJECTED,
            actor_id=actor_id,
            reason=override,
            department=target_department,
        )
    await db.commit()
    await db.refresh(ledger)

    return TransitionOutcome(
        ledger=ledger,
        step=CROSS_DEPT_STEP,
        result=REJECTED,
        previous_status=previous_status,
        next_status=ledger.status,
        skipped_steps=[],
        next_handlers=context.directory.refs(cross_dept_row_investigator_ids(entry, context.directory) or reviewer_ids),
        actor_name=actor_name,
        directory=context.directory,
        handlers=context.handlers,
        content=reason,
        elapsed_hours=elapsed_hours,
    )


async def submit_final_code(
    db: AsyncSession,
    *,
    ledger_id: uuid.UUID,
    final_code: str,
    actor_id: uuid.UUID,
    actor_name: str,
    actor_is_superuser: bool = False,
    override_reason: str | None = None,
) -> TransitionOutcome:
    """输入最终编号并关闭偏差。"""
    code = final_code.strip()
    if not code:
        raise BadRequestException("请输入最终编号")

    repo = DeviationLedgerRepository(db)
    ledger = await repo.get_by_id_for_update(ledger_id)
    if ledger is None:
        raise NotFoundException("偏差记录不存在")
    if ledger.status != LedgerStatus.PENDING_FINAL_CODE.value:
        raise BadRequestException(f"当前状态为「{constants.status_label(ledger.status)}」，不能输入最终编号")

    context = await build_flow_context(db, ledger)

    allowed = set(context.handlers.get("final_code_input", []))
    allowed.add(ledger.reporter_id)
    allowed.update(ledger.handler_ids or [])
    override = resolve_override_reason(
        actor_id, allowed, actor_is_superuser=actor_is_superuser, override_reason=override_reason
    )
    if not actor_is_superuser and allowed and actor_id not in allowed:
        raise ForbiddenException("最终编号由所属QA录入，你无权操作")

    previous_status = ledger.status
    ledger.final_code = code
    _append_opinion(
        ledger,
        step="final_code_input",
        result=APPROVED,
        actor_id=actor_id,
        actor_name=actor_name,
        content=f"最终编号：{code}",
        override_reason=override,
    )
    ledger.status = LedgerStatus.CLOSED.value
    ledger.status_updated_at = datetime.now(UTC)
    ledger.updated_by = actor_id
    if override:
        await record_override_audit(
            db, ledger=ledger, step="final_code_input", result=APPROVED, actor_id=actor_id, reason=override
        )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BadRequestException("该最终编号已被使用，请更换") from exc
    await db.refresh(ledger)

    return TransitionOutcome(
        ledger=ledger,
        step="final_code_input",
        result=APPROVED,
        previous_status=previous_status,
        next_status=ledger.status,
        skipped_steps=[],
        next_handlers=[],
        actor_name=actor_name,
        directory=context.directory,
        handlers=context.handlers,
    )


def step_payloads(context: FlowContext, ledger: DeviationLedger) -> list[dict[str, Any]]:
    """步骤条数据：环节、状态、责任角色、处理人、是否适用。"""
    payloads: list[dict[str, Any]] = []
    for definition in STEP_DEFS.values():
        applicable, skip_reason, auto_skip = step_note(ledger, definition.step)
        payload: dict[str, Any] = {
            "step": definition.step,
            "label": definition.label,
            "status": definition.status,
            "role_label": definition.role_label,
            "handlers": [{"id": str(ref.id), "name": ref.name} for ref in context.refs(definition.step)],
            "applicable": applicable,
            "skip_reason": skip_reason,
            "auto_skip": auto_skip,
        }
        if definition.step == CROSS_DEPT_STEP and applicable:
            payload["sub_items"] = cross_dept_row_payloads(ledger, context.contacts, context.directory)
        payloads.append(payload)
    return payloads


def dedupe(values: Iterable[uuid.UUID]) -> list[uuid.UUID]:
    """保序去重。"""
    seen: set[uuid.UUID] = set()
    result: list[uuid.UUID] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


__all__ = [
    "APPROVED",
    "CROSS_DEPT_INAPPLICABLE_REASON",
    "CROSS_DEPT_ROW_APPROVED",
    "CROSS_DEPT_ROW_PENDING",
    "CROSS_DEPT_STEP",
    "CROSS_DEPT_INVESTIGATION_PENDING",
    "CROSS_DEPT_INVESTIGATION_SUBMITTED",
    "QA_DEPARTMENT",
    "REJECTED",
    "RESUBMITTED",
    "STEP_DEFS",
    "STEP_ORDER",
    "STEP_TO_STATUS",
    "STATUS_TO_STEP",
    "FlowContext",
    "HandlerDirectory",
    "HandlerRef",
    "StepDef",
    "TransitionOutcome",
    "all_cross_dept_rows_approved",
    "approve_cross_dept_row",
    "build_flow_context",
    "cross_dept_review_rows",
    "cross_dept_row_investigator_ids",
    "cross_dept_row_payloads",
    "cross_dept_row_requires_investigation",
    "cross_dept_row_reviewer_ids",
    "is_cross_dept_row_approved",
    "is_cross_dept_row_investigated",
    "load_contacts",
    "needs_cross_dept_review",
    "resolve_step_handlers",
    "step_note",
    "step_payloads",
    "submit_final_code",
    "transition",
]
