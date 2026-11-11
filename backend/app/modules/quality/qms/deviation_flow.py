"""偏差台账流程内核：状态↔环节映射、处理人解析、统一流转入口。

设计取舍：业务是固定 SOP 的串行 12 态，不引入流程引擎、不建流程配置中心。
所有环节定义收敛在这张 ``STEP_DEFS`` 表里，流转只走 ``transition()`` 一个入口；
将来若要配置化，只需把 StepDef 换成表驱动，``transition()`` 是唯一改动点。

处理人全部来自 ``quality.department_contacts``：

- 调查人：台账 ``handler_ids``
- 部门负责人：本部门 ``dept_head_id``
- 跨部门负责人：``cross_dept_reviewers`` 中各跨部门部门的 ``dept_head_id``
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
from app.platform.identity.models import User

from . import deviation_ledger_constants as constants
from .deviation_department_models import DepartmentContact
from .deviation_ledger_constants import LedgerStatus
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
        department = str(entry.get("department") or "").strip()
        contact = contacts.get(department)
        if contact is not None and contact.dept_head_id is not None and contact.dept_head_id not in cross_ids:
            cross_ids.append(contact.dept_head_id)
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


def _append_opinion(
    ledger: DeviationLedger,
    *,
    step: str,
    result: str,
    actor_id: uuid.UUID,
    actor_name: str,
    content: str,
) -> None:
    opinion = {
        "step": step,
        "step_label": STEP_DEFS[step].label,
        "result": result,
        "author_id": str(actor_id),
        "author_name": actor_name,
        "content": content,
        "create_time": datetime.now(UTC).isoformat(),
    }
    ledger.review_opinions = [*(ledger.review_opinions or []), opinion]


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
    reason_category: str | None = None,
    deviation_level: str | None = None,
) -> TransitionOutcome:
    """统一流转入口：校验 → 守卫 → 追加意见 → 推进状态（含自动跳过）。"""
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

    context = await build_flow_context(db, ledger)

    if result != REJECTED and not actor_is_superuser:
        allowed = allowed_actors(ledger, step, context.handlers)
        if allowed and actor_id not in allowed:
            role_label = STEP_DEFS[step].role_label
            raise ForbiddenException(f"当前环节由{role_label}处理，你无权操作")

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

    _append_opinion(
        ledger,
        step=step,
        result=result,
        actor_id=actor_id,
        actor_name=actor_name,
        content=content.strip(),
    )

    skipped: list[str] = []
    if result == REJECTED:
        next_status = LedgerStatus.RETURNED.value
        ledger.returned_step = step
    elif result == RESUBMITTED:
        next_status = STEP_TO_STATUS[step]
    else:
        next_status = _next_status_on_approve(ledger, step)
        next_status, skipped = _apply_auto_skip(next_status, context.handlers)

    now = datetime.now(UTC)
    elapsed_hours = _elapsed_hours(ledger.status_updated_at, now)
    ledger.status = next_status
    ledger.status_updated_at = now
    ledger.updated_by = actor_id
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


async def submit_final_code(
    db: AsyncSession,
    *,
    ledger_id: uuid.UUID,
    final_code: str,
    actor_id: uuid.UUID,
    actor_name: str,
    actor_is_superuser: bool = False,
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
    )
    ledger.status = LedgerStatus.CLOSED.value
    ledger.status_updated_at = datetime.now(UTC)
    ledger.updated_by = actor_id
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
        payloads.append(
            {
                "step": definition.step,
                "label": definition.label,
                "status": definition.status,
                "role_label": definition.role_label,
                "handlers": [{"id": str(ref.id), "name": ref.name} for ref in context.refs(definition.step)],
                "applicable": applicable,
                "skip_reason": skip_reason,
                "auto_skip": auto_skip,
            }
        )
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
    "CROSS_DEPT_STEP",
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
    "build_flow_context",
    "load_contacts",
    "needs_cross_dept_review",
    "resolve_step_handlers",
    "step_note",
    "step_payloads",
    "submit_final_code",
    "transition",
]
