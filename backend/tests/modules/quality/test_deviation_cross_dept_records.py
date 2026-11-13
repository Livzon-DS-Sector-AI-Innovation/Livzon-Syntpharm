"""跨部门逐行审核与结构化调查记录（不依赖真实数据库）。

覆盖本轮三项改造的后端口径：

- 跨部门行审核人 = 行内调查人，为空回退该部门负责人；环节处理人为各行并集；
- 跨部门审核必须逐行通过，全部行通过后环节才前进到所属 QA 审核；
  整环节「通过」被拒绝，退回重提后已通过的行保持通过；
- 待调查阶段仅上报人/调查人可增删改跨部门名单，其余字段拒绝；
- 调查记录结构化为四区 + CAPA + 紧急措施 + 记录级附件快照，
  悬挂 file_id 拒绝，旧纯文本记录字段保持可读。
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage as core_storage
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.modules.quality.qms import deviation_flow
from app.modules.quality.qms import deviation_ledger_service as service_module
from app.modules.quality.qms.deviation_department_models import DepartmentContact
from app.modules.quality.qms.deviation_flow import (
    APPROVED,
    CROSS_DEPT_INVESTIGATION_PENDING,
    CROSS_DEPT_INVESTIGATION_SUBMITTED,
    CROSS_DEPT_ROW_APPROVED,
    CROSS_DEPT_ROW_PENDING,
    CROSS_DEPT_STEP,
    RESUBMITTED,
    FlowContext,
    HandlerDirectory,
    HandlerRef,
    TransitionOutcome,
    all_cross_dept_rows_approved,
    approve_cross_dept_row,
    cross_dept_row_payloads,
    cross_dept_row_reviewer_ids,
    resolve_step_handlers,
    step_payloads,
    transition,
)
from app.modules.quality.qms.deviation_ledger_constants import LedgerStatus
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger
from app.modules.quality.qms.deviation_ledger_schemas import (
    CapaProposalItem,
    CrossDeptApproveRequest,
    CrossDeptInvestigationRequest,
    CrossDeptReviewerItem,
    InvestigationRecordItem,
    InvestigationRequest,
    LedgerCreateRequest,
    LedgerDetail,
    LedgerUpdateRequest,
)
from app.modules.quality.qms.deviation_ledger_service import (
    DeviationLedgerService,
    _merge_cross_dept_states,
    _normalized_cross_dept_rows,
)

# ── 公共构造器 ──────────────────────────────────────────────────────────


def _ref(name: str) -> HandlerRef:
    return HandlerRef(id=uuid.uuid4(), name=name)


def _directory(*refs: HandlerRef) -> HandlerDirectory:
    return HandlerDirectory({ref.id: ref for ref in refs})


def _contact(department: str, **overrides: Any) -> DepartmentContact:
    return DepartmentContact(department=department, **overrides)


def _row_ledger(**overrides: Any) -> DeviationLedger:
    now = datetime.now(UTC)
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "code": "PC20261112001",
        "title": "偏差标题",
        "department": "101车间",
        "status": LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        "status_updated_at": now,
        "reporter_id": uuid.uuid4(),
        "handler_ids": [],
        "needs_cross_dept_review": True,
        "cross_dept_reviewers": [],
        "review_opinions": [],
        "investigation_records": [],
        "created_at": now,
        "updated_at": now,
        "is_deleted": False,
    }
    base.update(overrides)
    return DeviationLedger(**base)


def _row(department: str, investigator_ids: list[str], **state: Any) -> dict[str, Any]:
    return {"department": department, "investigator_ids": investigator_ids, **state}


# ── 行审核人解析（纯函数） ──────────────────────────────────────────────


def test_row_reviewer_prefers_row_dept_head() -> None:
    """两节点：审核人是行内显式指定的部门负责人，调查人不再兼任审核人。"""
    investigator = _ref("张三")
    head = _ref("李四")
    contacts = {"设备部": _contact("设备部", dept_head_id=uuid.uuid4())}
    entry = _row("设备部", [str(investigator.id)], dept_head_id=str(head.id))

    assert cross_dept_row_reviewer_ids(entry, contacts, _directory(investigator, head)) == [head.id]


def test_row_reviewer_falls_back_to_dept_head() -> None:
    head = _ref("李四")
    contacts = {"设备部": _contact("设备部", dept_head_id=head.id)}

    assert cross_dept_row_reviewer_ids(_row("设备部", []), contacts, _directory(head)) == [head.id]


def test_row_reviewer_ignores_investigators_without_head() -> None:
    """存量行缺行内负责人且联系人未配置时，调查人不会被当作审核人。"""
    investigator = _ref("张三")

    assert cross_dept_row_reviewer_ids(_row("设备部", [str(investigator.id)]), {}, _directory(investigator)) == []


def test_row_reviewer_empty_when_no_investigator_and_no_contact() -> None:
    assert cross_dept_row_reviewer_ids(_row("设备部", []), {}, _directory()) == []


def test_all_rows_approved_requires_rows_and_every_state() -> None:
    assert all_cross_dept_rows_approved(_row_ledger(cross_dept_reviewers=[])) is False
    mixed = _row_ledger(
        cross_dept_reviewers=[
            _row("设备部", [], review_state=CROSS_DEPT_ROW_APPROVED),
            _row("生产部", []),
        ]
    )
    assert all_cross_dept_rows_approved(mixed) is False
    done = _row_ledger(
        cross_dept_reviewers=[
            _row("设备部", [], review_state=CROSS_DEPT_ROW_APPROVED),
            _row("生产部", [], review_state=CROSS_DEPT_ROW_APPROVED),
        ]
    )
    assert all_cross_dept_rows_approved(done) is True


def test_resolve_handlers_cross_dept_is_row_head_union_deduped() -> None:
    head_a = _ref("李四")
    head_b = _ref("王五")
    head_c = _ref("赵六")
    investigator = _ref("张三")
    ledger = _row_ledger(
        cross_dept_reviewers=[
            _row("设备部", [str(investigator.id)], dept_head_id=str(head_a.id)),
            _row("生产部", [str(investigator.id), str(head_b.id)]),
            _row("工程部", [], dept_head_id=str(head_b.id)),
        ]
    )
    contacts = {"生产部": _contact("生产部", dept_head_id=head_c.id)}

    handlers = resolve_step_handlers(ledger, contacts, _directory(head_a, head_b, head_c, investigator))

    # 行内负责人优先；行内缺省回退部门联系人；调查人不参与审核环节
    assert handlers[CROSS_DEPT_STEP] == [head_a.id, head_c.id, head_b.id]


def test_row_payloads_display_two_nodes_and_names() -> None:
    investigator = _ref("张三")
    head = _ref("李四")
    ledger = _row_ledger(
        cross_dept_reviewers=[
            _row(
                "设备部",
                [],
                dept_head_id=str(head.id),
                investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED,
                review_state=CROSS_DEPT_ROW_APPROVED,
                approved_name="李四",
                approved_at="2026-11-12T08:00:00+00:00",
                opinion="同意",
            ),
            _row("生产部", [str(investigator.id)], dept_head_id=str(head.id)),
            "脏数据",
        ]
    )
    contacts: dict[str, DepartmentContact] = {}

    payloads = cross_dept_row_payloads(ledger, contacts, _directory(investigator, head))

    assert [item["department"] for item in payloads] == ["设备部", "生产部"]
    assert payloads[0]["state"] == CROSS_DEPT_ROW_APPROVED
    assert payloads[0]["reviewer_names"] == ["李四"]
    assert payloads[0]["investigate_state"] == CROSS_DEPT_INVESTIGATION_SUBMITTED
    assert payloads[0]["approved_by_name"] == "李四"
    assert payloads[0]["opinion"] == "同意"
    assert payloads[1]["state"] == CROSS_DEPT_ROW_PENDING
    assert payloads[1]["reviewer_names"] == ["李四"]
    assert payloads[1]["investigate_state"] == CROSS_DEPT_INVESTIGATION_PENDING


def test_step_payloads_sub_items_only_for_cross_dept_step() -> None:
    investigator = _ref("张三")
    head = _ref("李四")
    ledger = _row_ledger(cross_dept_reviewers=[_row("设备部", [str(investigator.id)], dept_head_id=str(head.id))])
    contacts: dict[str, DepartmentContact] = {}
    directory = _directory(investigator, head)
    context = FlowContext(
        contacts=contacts,
        directory=directory,
        handlers=resolve_step_handlers(ledger, contacts, directory),
    )

    payloads = {item["step"]: item for item in step_payloads(context, ledger)}

    assert payloads[CROSS_DEPT_STEP]["sub_items"] == [
        {
            "department": "设备部",
            "reviewer_names": ["李四"],
            "investigate_state": CROSS_DEPT_INVESTIGATION_PENDING,
            "state": CROSS_DEPT_ROW_PENDING,
            "approved_by_name": None,
            "approved_at": None,
            "opinion": None,
        }
    ]
    other = next(item for step, item in payloads.items() if step != CROSS_DEPT_STEP)
    assert "sub_items" not in other

    disabled = _row_ledger(needs_cross_dept_review=False, cross_dept_reviewers=[])
    off_payloads = {item["step"]: item for item in step_payloads(context, disabled)}
    assert off_payloads[CROSS_DEPT_STEP]["applicable"] is False
    assert "sub_items" not in off_payloads[CROSS_DEPT_STEP]


# ── 流转函数（monkeypatch 仓储与上下文） ────────────────────────────────


class _FlowDB:
    """flow 函数需要的最小会话替身：commit/refresh 计数，查询不会被真实执行。"""

    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: Any) -> None:
        return None


def _patch_flow(monkeypatch: pytest.MonkeyPatch, ledger: DeviationLedger, context: FlowContext) -> None:
    async def fake_build_flow_context(db: AsyncSession, row: DeviationLedger) -> FlowContext:
        return context

    class _Repo:
        def __init__(self, db: AsyncSession) -> None:
            self.db = db

        async def get_by_id_for_update(self, ledger_id: uuid.UUID) -> DeviationLedger | None:
            return ledger if ledger_id == ledger.id else None

    monkeypatch.setattr(deviation_flow, "DeviationLedgerRepository", _Repo)
    monkeypatch.setattr(deviation_flow, "build_flow_context", fake_build_flow_context)


def _cross_dept_context(
    ledger: DeviationLedger,
    *refs: HandlerRef,
    qa_reviewer: HandlerRef | None = None,
) -> FlowContext:
    contacts: dict[str, DepartmentContact] = {}
    if qa_reviewer is not None:
        department = ledger.department or ""
        contacts[department] = _contact(department, qa_reviewer_id=qa_reviewer.id)
    directory = _directory(*refs)
    handlers = resolve_step_handlers(ledger, contacts, directory)
    return FlowContext(contacts=contacts, directory=directory, handlers=handlers)


async def test_transition_rejects_whole_step_cross_dept_approve(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _ref("张三")
    ledger = _row_ledger(cross_dept_reviewers=[_row("设备部", [str(reviewer.id)])])
    _patch_flow(monkeypatch, ledger, _cross_dept_context(ledger, reviewer))

    with pytest.raises(BadRequestException) as excinfo:
        await transition(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger.id,
            step=CROSS_DEPT_STEP,
            result=APPROVED,
            content="",
            actor_id=reviewer.id,
            actor_name="张三",
        )
    assert "逐行" in str(excinfo.value)


async def test_approve_row_partial_keeps_step(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer_a = _ref("张三")
    reviewer_b = _ref("李四")
    qa = _ref("王五")
    ledger = _row_ledger(
        cross_dept_reviewers=[
            _row("设备部", [], dept_head_id=str(reviewer_a.id)),
            _row("生产部", [], dept_head_id=str(reviewer_b.id)),
        ]
    )
    context = _cross_dept_context(ledger, reviewer_a, reviewer_b, qa, qa_reviewer=qa)
    _patch_flow(monkeypatch, ledger, context)
    db = _FlowDB()

    outcome = await approve_cross_dept_row(
        cast(AsyncSession, db),
        ledger_id=ledger.id,
        department="设备部",
        content="设备无异议",
        actor_id=reviewer_a.id,
        actor_name="张三",
    )

    assert outcome.next_status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    assert ledger.status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    rows = {str(item["department"]): item for item in ledger.cross_dept_reviewers or []}
    assert rows["设备部"]["review_state"] == CROSS_DEPT_ROW_APPROVED
    assert rows["设备部"]["approved_name"] == "张三"
    assert rows["设备部"]["opinion"] == "设备无异议"
    assert rows["生产部"].get("review_state") is None
    assert outcome.elapsed_hours is None
    assert db.commits == 1


async def test_approve_row_blocked_until_investigation_submitted(monkeypatch: pytest.MonkeyPatch) -> None:
    """两节点顺序：配置了行内调查人的行，必须先提交调查才允许部门负责人审核。"""
    investigator = _ref("张三")
    head = _ref("李四")
    qa = _ref("王五")
    ledger = _row_ledger(cross_dept_reviewers=[_row("设备部", [str(investigator.id)], dept_head_id=str(head.id))])
    _patch_flow(monkeypatch, ledger, _cross_dept_context(ledger, investigator, head, qa, qa_reviewer=qa))

    with pytest.raises(BadRequestException, match="调查尚未提交"):
        await approve_cross_dept_row(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger.id,
            department="设备部",
            content="",
            actor_id=head.id,
            actor_name="李四",
        )

    ledger.cross_dept_reviewers = [
        _row(
            "设备部",
            [str(investigator.id)],
            dept_head_id=str(head.id),
            investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED,
        )
    ]
    outcome = await approve_cross_dept_row(
        cast(AsyncSession, _FlowDB()),
        ledger_id=ledger.id,
        department="设备部",
        content="同意",
        actor_id=head.id,
        actor_name="李四",
    )
    assert outcome.next_status == LedgerStatus.PENDING_QA_REVIEW.value


async def test_approve_last_row_advances_to_qa(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer_a = _ref("张三")
    reviewer_b = _ref("李四")
    qa = _ref("王五")
    ledger = _row_ledger(
        cross_dept_reviewers=[
            _row("设备部", [], dept_head_id=str(reviewer_a.id), review_state=CROSS_DEPT_ROW_APPROVED),
            _row("生产部", [], dept_head_id=str(reviewer_b.id)),
        ]
    )
    context = _cross_dept_context(ledger, reviewer_a, reviewer_b, qa, qa_reviewer=qa)
    _patch_flow(monkeypatch, ledger, context)

    outcome = await approve_cross_dept_row(
        cast(AsyncSession, _FlowDB()),
        ledger_id=ledger.id,
        department="生产部",
        content="",
        actor_id=reviewer_b.id,
        actor_name="李四",
    )

    assert outcome.previous_status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    assert outcome.next_status == LedgerStatus.PENDING_QA_REVIEW.value
    assert ledger.status == LedgerStatus.PENDING_QA_REVIEW.value
    assert all_cross_dept_rows_approved(ledger) is True


async def test_approve_row_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _ref("张三")
    stranger = _ref("路人")
    qa = _ref("王五")

    approved_rows = [_row("设备部", [], dept_head_id=str(reviewer.id), review_state=CROSS_DEPT_ROW_APPROVED)]
    ledger = _row_ledger(cross_dept_reviewers=list(approved_rows))
    _patch_flow(monkeypatch, ledger, _cross_dept_context(ledger, reviewer, stranger, qa))
    with pytest.raises(BadRequestException, match="无需重复审批"):
        await approve_cross_dept_row(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger.id,
            department="设备部",
            content="",
            actor_id=reviewer.id,
            actor_name="张三",
        )

    with pytest.raises(NotFoundException, match="跨部门行不存在"):
        await approve_cross_dept_row(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger.id,
            department="不存在的部",
            content="",
            actor_id=reviewer.id,
            actor_name="张三",
        )

    pending_rows = [_row("设备部", [], dept_head_id=str(reviewer.id)), _row("生产部", [], dept_head_id=str(qa.id))]
    ledger2 = _row_ledger(cross_dept_reviewers=pending_rows)
    _patch_flow(monkeypatch, ledger2, _cross_dept_context(ledger2, reviewer, stranger, qa))
    with pytest.raises(ForbiddenException, match="审核人"):
        await approve_cross_dept_row(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger2.id,
            department="设备部",
            content="",
            actor_id=stranger.id,
            actor_name="路人",
        )

    ledger3 = _row_ledger(cross_dept_reviewers=[_row("工程部", [])], status=LedgerStatus.PENDING_QA_REVIEW.value)
    _patch_flow(monkeypatch, ledger3, _cross_dept_context(ledger3, reviewer, qa))
    with pytest.raises(BadRequestException, match="不能按部门审批"):
        await approve_cross_dept_row(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger3.id,
            department="工程部",
            content="",
            actor_id=reviewer.id,
            actor_name="张三",
        )

    ledger4 = _row_ledger(cross_dept_reviewers=[_row("工程部", [])])
    _patch_flow(monkeypatch, ledger4, _cross_dept_context(ledger4, reviewer, qa))
    with pytest.raises(BadRequestException, match="没有审核人"):
        await approve_cross_dept_row(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger4.id,
            department="工程部",
            content="",
            actor_id=reviewer.id,
            actor_name="张三",
        )


async def test_resubmit_after_return_keeps_approved_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """跨部门环节被整环节退回后重提：回到本环节，已通过行保持通过、只审未完成行。"""
    reviewer_a = _ref("张三")
    reviewer_b = _ref("李四")
    qa = _ref("王五")
    ledger = _row_ledger(
        status=LedgerStatus.RETURNED.value,
        returned_step=CROSS_DEPT_STEP,
        reporter_id=reviewer_a.id,
        cross_dept_reviewers=[
            _row("设备部", [str(reviewer_a.id)], review_state=CROSS_DEPT_ROW_APPROVED),
            _row("生产部", [str(reviewer_b.id)]),
        ],
    )
    context = _cross_dept_context(ledger, reviewer_a, reviewer_b, qa, qa_reviewer=qa)
    _patch_flow(monkeypatch, ledger, context)

    outcome = await transition(
        cast(AsyncSession, _FlowDB()),
        ledger_id=ledger.id,
        step=CROSS_DEPT_STEP,
        result=RESUBMITTED,
        content="补充说明后重新提交",
        actor_id=reviewer_a.id,
        actor_name="张三",
    )

    assert outcome.next_status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    rows = {str(item["department"]): item for item in ledger.cross_dept_reviewers or []}
    assert rows["设备部"]["review_state"] == CROSS_DEPT_ROW_APPROVED
    assert rows["生产部"].get("review_state") is None


# ── schemas 校验（纯函数） ──────────────────────────────────────────────


def _create_payload(**overrides: Any) -> LedgerCreateRequest:
    base: dict[str, Any] = {
        "title": "偏差标题",
        "department": "101车间",
        "discovery_date": date(2026, 11, 12),
        "discovery_time": "09:05",
        "discovery_location": "洁净区",
        "affected_items": "某产品",
        "batch_number": "B001",
        "handler_ids": [uuid.uuid4()],
        "description": "描述",
    }
    base.update(overrides)
    return LedgerCreateRequest(**base)


def _investigation_payload(**overrides: Any) -> InvestigationRequest:
    base: dict[str, Any] = {
        "nonconformity_description": "描述不符合事项",
        "root_cause_analysis": "原因分析",
        "risk_assessment": "风险评估",
        "capa_proposals": [CapaProposalItem(summary="整改内容")],
    }
    base.update(overrides)
    return InvestigationRequest(**base)


def test_create_rejects_duplicate_or_empty_cross_dept_departments() -> None:
    head = uuid.uuid4()
    payload = _create_payload(
        needs_cross_dept_review=True,
        cross_dept_reviewers=[CrossDeptReviewerItem(department=" 设备部 ", dept_head_id=head)],
    )
    assert [row.department for row in payload.cross_dept_reviewers] == ["设备部"]
    rows = [
        CrossDeptReviewerItem(department="设备部", dept_head_id=head),
        CrossDeptReviewerItem(department=" 设备部 ", dept_head_id=head),
    ]
    with pytest.raises(ValueError, match="重复"):
        _create_payload(needs_cross_dept_review=True, cross_dept_reviewers=rows)
    with pytest.raises(ValueError, match="至少"):
        _create_payload(needs_cross_dept_review=True, cross_dept_reviewers=[])
    with pytest.raises(ValueError, match="不能为空"):
        _create_payload(
            needs_cross_dept_review=True,
            cross_dept_reviewers=[CrossDeptReviewerItem(department="  ", dept_head_id=head)],
        )
    with pytest.raises(ValueError, match="部门负责人"):
        _create_payload(needs_cross_dept_review=True, cross_dept_reviewers=[CrossDeptReviewerItem(department="设备部")])
    assert _create_payload(needs_cross_dept_review=False, cross_dept_reviewers=[]).cross_dept_reviewers == []


def test_update_validates_cross_dept_rows() -> None:
    head = uuid.uuid4()
    with pytest.raises(ValueError, match="重复"):
        LedgerUpdateRequest(
            needs_cross_dept_review=True,
            cross_dept_reviewers=[
                CrossDeptReviewerItem(department="设备部", dept_head_id=head),
                CrossDeptReviewerItem(department="设备部", dept_head_id=head),
            ],
        )
    with pytest.raises(ValueError, match="部门负责人"):
        LedgerUpdateRequest(cross_dept_reviewers=[CrossDeptReviewerItem(department="生产部")])
    payload = LedgerUpdateRequest(
        cross_dept_reviewers=[CrossDeptReviewerItem(department=" 生产部 ", dept_head_id=head)]
    )
    assert payload.cross_dept_reviewers is not None
    assert payload.cross_dept_reviewers[0].department == "生产部"
    assert payload.cross_dept_reviewers[0].dept_head_id == head


def test_cross_dept_approve_request_requires_department() -> None:
    with pytest.raises(ValueError, match="不能为空"):
        CrossDeptApproveRequest(department="   ")
    assert CrossDeptApproveRequest(department=" 设备部 ").department == "设备部"
    assert CrossDeptApproveRequest(department="设备部").opinion == ""


def test_investigation_attachment_route_allows_empty_texts_and_capa() -> None:
    """二选一规则：引用 ≥1 个台账附件（调查报告）时，三个文本与 CAPA 均可空。"""
    payload = _investigation_payload(
        nonconformity_description="",
        root_cause_analysis="",
        risk_assessment="",
        capa_proposals=[],
        attachment_file_ids=[uuid.uuid4()],
    )
    assert payload.nonconformity_description == ""
    assert payload.capa_proposals == []
    assert len(payload.attachment_file_ids) == 1


def test_investigation_requires_three_texts_and_one_capa() -> None:
    """未引用附件时维持原必填规则：文本非空 + CAPA 至少一条。"""
    _investigation_payload()
    for field in ("nonconformity_description", "root_cause_analysis", "risk_assessment"):
        with pytest.raises(ValueError):
            _investigation_payload(**{field: "   "})
        with pytest.raises(ValueError):
            _investigation_payload(**{field: None})
    with pytest.raises(ValueError):
        _investigation_payload(capa_proposals=[])
    with pytest.raises(ValueError, match="CAPA"):
        _investigation_payload(capa_proposals=[CapaProposalItem(summary="  ")])
    with pytest.raises(ValueError, match="附件"):
        _investigation_payload(nonconformity_description="", root_cause_analysis="", risk_assessment="")
    with pytest.raises(ValueError, match="附件"):
        _investigation_payload(capa_proposals=[])


def test_investigation_urgent_and_attachments() -> None:
    assert _investigation_payload(urgent_measures=" 隔离批次 ").urgent_measures == "隔离批次"
    assert _investigation_payload(urgent_measures=None).urgent_measures is None
    with pytest.raises(ValueError, match="紧急"):
        _investigation_payload(urgent_measures="   ")
    repeated = uuid.uuid4()
    payload = _investigation_payload(attachment_file_ids=[repeated, uuid.uuid4(), repeated])
    assert payload.attachment_file_ids is not None
    assert payload.attachment_file_ids[0] == repeated
    assert len(payload.attachment_file_ids) == 2


def test_record_item_keeps_legacy_content_readable() -> None:
    legacy = InvestigationRecordItem(content="旧格式：仅纯文本记录")
    assert legacy.content == "旧格式：仅纯文本记录"
    assert legacy.nonconformity_description == ""
    assert legacy.capa_proposals == []
    assert legacy.attachments == []
    assert legacy.urgent_measures is None


# ── service 共用构造器与守卫 ────────────────────────────────────────────


class _Service(DeviationLedgerService):
    """守卫测试不关心详情组装与通知发送：替换为无副作用实现。"""

    async def _build_detail(
        self,
        row: DeviationLedger,
        *,
        viewer_id: uuid.UUID | None = None,
        viewer_is_superuser: bool = False,
    ) -> LedgerDetail:
        return cast(LedgerDetail, row)

    def _schedule_transition_notice(self, outcome: TransitionOutcome) -> None:
        return None


class _RowRepo:
    def __init__(self, row: DeviationLedger | None) -> None:
        self.row = row

    async def get_by_id_for_update(self, ledger_id: uuid.UUID) -> DeviationLedger | None:
        return self.row if self.row is not None and ledger_id == self.row.id else None

    async def get_by_id(self, ledger_id: uuid.UUID) -> DeviationLedger | None:
        return self.row if self.row is not None and ledger_id == self.row.id else None


class _NoopResult:
    """UPDATE/DELETE 的结果替身，只需要 rowcount。"""

    rowcount = 0


class _ServiceDB:
    def __init__(self) -> None:
        self.commits = 0
        self.statements: list[Any] = []

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: Any) -> None:
        return None

    async def execute(self, statement: Any) -> _NoopResult:
        # remove_attachment 会级联软删批注（UPDATE），这里只记录不执行
        self.statements.append(statement)
        return _NoopResult()


def _service(row: DeviationLedger | None) -> tuple[_Service, _ServiceDB]:
    db = _ServiceDB()
    service = _Service(cast(AsyncSession, db))
    service.repo = cast(Any, _RowRepo(row))
    return service, db


def _record_row(**overrides: Any) -> DeviationLedger:
    file_id = overrides.pop("file_id", uuid.uuid4())
    row = _row_ledger(**overrides)
    row.attachments = [
        {
            "file_id": str(file_id),
            "file_name": "调查证据.pdf",
            "size": 1024,
            "content_type": "application/pdf",
            "uploaded_by": str(row.reporter_id),
            "uploaded_by_name": "上报人",
            "uploaded_at": "2026-11-12T07:00:00+00:00",
        }
    ]
    return row


def test_normalized_rows_keep_department_investigators_and_head() -> None:
    person = uuid.uuid4()
    head = uuid.uuid4()
    rows = _normalized_cross_dept_rows(
        [
            CrossDeptReviewerItem(
                department="设备部",
                investigator_ids=[person],
                dept_head_id=head,
                review_state=CROSS_DEPT_ROW_APPROVED,
                approved_name="李四",
                opinion="过期状态",
            )
        ]
    )
    assert rows == [{"department": "设备部", "investigator_ids": [str(person)], "dept_head_id": str(head)}]


def test_merge_states_keeps_identical_and_resets_changed() -> None:
    person = uuid.uuid4()
    other = uuid.uuid4()
    head = uuid.uuid4()
    approved = {
        "department": "设备部",
        "investigator_ids": [str(person)],
        "dept_head_id": str(head),
        "investigate_state": CROSS_DEPT_INVESTIGATION_SUBMITTED,
        "review_state": CROSS_DEPT_ROW_APPROVED,
        "approved_by": str(person),
        "approved_name": "张三",
        "approved_at": "2026-11-12T08:00:00+00:00",
        "opinion": "同意",
    }
    merged = _merge_cross_dept_states(
        [approved],
        [
            {"department": "设备部", "investigator_ids": [str(person)], "dept_head_id": str(head)},
            {"department": "设备部", "investigator_ids": [str(other)], "dept_head_id": str(head)},
            {"department": "设备部", "investigator_ids": [str(person)], "dept_head_id": str(other)},
        ],
    )
    assert merged[0]["review_state"] == CROSS_DEPT_ROW_APPROVED
    assert merged[0]["approved_name"] == "张三"
    assert merged[0]["investigate_state"] == CROSS_DEPT_INVESTIGATION_SUBMITTED
    assert "review_state" not in merged[1]
    assert "review_state" not in merged[2]


def test_merge_states_keeps_investigation_progress_for_pending_row() -> None:
    """未通过的行改了基础信息后，部门调查进度不应被重置回待调查。"""
    person = uuid.uuid4()
    head = uuid.uuid4()
    investigated = {
        "department": "设备部",
        "investigator_ids": [str(person)],
        "dept_head_id": str(head),
        "investigate_state": CROSS_DEPT_INVESTIGATION_SUBMITTED,
        "investigate_submitted_by": str(person),
        "investigate_submitted_name": "李四",
        "investigate_submitted_at": "2026-11-12T09:00:00+00:00",
        "review_state": CROSS_DEPT_ROW_PENDING,
    }
    merged = _merge_cross_dept_states(
        [investigated],
        [{"department": "设备部", "investigator_ids": [str(person)], "dept_head_id": str(head)}],
    )
    assert merged[0]["investigate_state"] == CROSS_DEPT_INVESTIGATION_SUBMITTED
    assert merged[0]["investigate_submitted_by"] == str(person)
    assert merged[0]["investigate_submitted_name"] == "李四"
    # 保留的是调查进度，审核状态仍为待审
    assert "review_state" not in merged[0]


def test_build_record_renumbers_capa_and_snapshots_attachments() -> None:
    row = _record_row()
    file_id = uuid.UUID(str(row.attachments[0]["file_id"]))
    service = _Service(cast(AsyncSession, _ServiceDB()))
    payload = _investigation_payload(
        capa_proposals=[
            CapaProposalItem(
                sequence=7,
                summary=" 修订SOP ",
                executor=" 张三 ",
                expected_completion_date=date(2026, 12, 1),
            ),
            CapaProposalItem(sequence=99, summary="培训", expected_completion_date=None),
        ],
        urgent_measures="隔离批次",
        attachment_file_ids=[file_id, file_id],
    )

    record = service._build_investigation_record(row, payload, actor_id=row.reporter_id, actor_name="上报人")

    assert [item["sequence"] for item in record["capa_proposals"]] == [1, 2]
    assert record["capa_proposals"][0]["summary"] == "修订SOP"
    assert record["capa_proposals"][0]["executor"] == "张三"
    assert record["capa_proposals"][0]["expected_completion_date"] == "2026-12-01"
    assert record["capa_proposals"][1]["expected_completion_date"] is None
    assert record["urgent_measures"] == "隔离批次"
    assert record["nonconformity_description"] == "描述不符合事项"
    assert len(record["attachments"]) == 1
    assert record["attachments"][0]["file_name"] == "调查证据.pdf"
    assert record["author_id"] == str(row.reporter_id)


def test_build_record_rejects_dangling_file_id() -> None:
    service = _Service(cast(AsyncSession, _ServiceDB()))
    payload = _investigation_payload(attachment_file_ids=[uuid.uuid4()])
    with pytest.raises(BadRequestException, match="附件不存在"):
        service._build_investigation_record(_record_row(), payload, actor_id=uuid.uuid4(), actor_name="调查人")


async def test_update_investigation_stage_locks_non_cross_dept_fields() -> None:
    investigator = uuid.uuid4()
    reporter = uuid.uuid4()
    row = _row_ledger(
        status=LedgerStatus.PENDING_INVESTIGATION.value,
        reporter_id=reporter,
        handler_ids=[investigator],
        cross_dept_reviewers=[],
    )
    service, _db = _service(row)

    with pytest.raises(BadRequestException, match="只能修改跨部门"):
        await service.update(row.id, LedgerUpdateRequest(title="新标题"), actor_id=investigator, actor_name="调查人")
    head = uuid.uuid4()
    with pytest.raises(ForbiddenException, match="跨部门审核配置"):
        await service.update(
            row.id,
            LedgerUpdateRequest(
                needs_cross_dept_review=True,
                cross_dept_reviewers=[CrossDeptReviewerItem(department="设备部", dept_head_id=head)],
            ),
            actor_id=uuid.uuid4(),
            actor_name="路人",
        )

    await service.update(
        row.id,
        LedgerUpdateRequest(
            needs_cross_dept_review=True,
            cross_dept_reviewers=[CrossDeptReviewerItem(department=" 设备部 ", dept_head_id=head)],
        ),
        actor_id=investigator,
        actor_name="调查人",
    )
    assert row.needs_cross_dept_review is True
    assert row.cross_dept_reviewers == [{"department": "设备部", "investigator_ids": [], "dept_head_id": str(head)}]

    await service.update(
        row.id,
        LedgerUpdateRequest(needs_cross_dept_review=False),
        actor_id=reporter,
        actor_name="上报人",
    )
    assert row.cross_dept_reviewers is None


async def test_update_blocked_outside_investigation_stage() -> None:
    row = _row_ledger(status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value)
    service, _db = _service(row)
    with pytest.raises(BadRequestException, match="不允许修改基础信息"):
        await service.update(
            row.id,
            LedgerUpdateRequest(
                cross_dept_reviewers=[CrossDeptReviewerItem(department="设备部", dept_head_id=uuid.uuid4())]
            ),
            actor_id=row.reporter_id,
            actor_name="上报人",
        )


async def test_append_record_guards_and_appends_without_transition() -> None:
    investigator = uuid.uuid4()
    file_id = uuid.uuid4()
    row = _record_row(file_id=file_id, status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value, handler_ids=[investigator])
    row.investigation_records = [{"content": "旧记录"}]
    service, db = _service(row)
    payload = _investigation_payload(attachment_file_ids=[file_id])

    with pytest.raises(ForbiddenException, match="调查人"):
        await service.append_investigation_record(row.id, payload, actor_id=uuid.uuid4(), actor_name="路人")

    locked = _row_ledger(status=LedgerStatus.PENDING_AI_ANALYSIS.value, handler_ids=[investigator])
    locked_service, _locked_db = _service(locked)
    with pytest.raises(BadRequestException, match="新增调查记录"):
        await locked_service.append_investigation_record(locked.id, payload, actor_id=investigator, actor_name="调查人")

    await service.append_investigation_record(row.id, payload, actor_id=investigator, actor_name="调查人")

    assert row.status == LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value
    assert len(row.investigation_records or []) == 2
    appended = (row.investigation_records or [])[1]
    assert appended["nonconformity_description"] == "描述不符合事项"
    assert appended["attachments"][0]["file_id"] == str(file_id)
    assert db.commits == 1


def test_cross_dept_investigator_can_maintain_investigation_docs() -> None:
    """跨部门行调查人可上传/删除本部门调查报告（附件路线前提）。"""
    investigator = uuid.uuid4()
    row = _row_ledger(
        cross_dept_reviewers=[
            {
                "department": "设备部",
                "investigator_ids": [str(investigator)],
                "dept_head_id": str(uuid.uuid4()),
            }
        ]
    )
    service, _db = _service(row)

    service._assert_can_edit_investigation(row, investigator)
    with pytest.raises(ForbiddenException, match="调查人"):
        service._assert_can_edit_investigation(row, uuid.uuid4())


async def test_submit_cross_dept_investigation_marks_row_and_tags_record() -> None:
    """跨部门调查节点：只标记该行「调查已提交」并落部门标记记录，不推进台账状态。"""
    investigator = uuid.uuid4()
    head = uuid.uuid4()
    file_id = uuid.uuid4()
    row = _record_row(
        file_id=file_id,
        cross_dept_reviewers=[
            {"department": "设备部", "investigator_ids": [str(investigator)], "dept_head_id": str(head)}
        ],
    )
    service, db = _service(row)
    payload = CrossDeptInvestigationRequest(
        department=" 设备部 ",
        nonconformity_description="",
        root_cause_analysis="",
        risk_assessment="",
        capa_proposals=[],
        attachment_file_ids=[file_id],
    )

    await service.submit_cross_dept_investigation(row.id, payload, actor_id=investigator, actor_name="张三")

    entry = (row.cross_dept_reviewers or [])[0]
    assert entry["investigate_state"] == CROSS_DEPT_INVESTIGATION_SUBMITTED
    assert entry["investigate_submitted_name"] == "张三"
    assert entry["investigate_submitted_by"] == str(investigator)
    assert row.status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    record = (row.investigation_records or [])[0]
    assert record["department"] == "设备部"
    assert record["attachments"][0]["file_id"] == str(file_id)
    assert db.commits == 1


async def test_submit_cross_dept_investigation_guards() -> None:
    investigator = uuid.uuid4()
    head = uuid.uuid4()
    stranger = uuid.uuid4()
    row = _row_ledger(
        cross_dept_reviewers=[
            {"department": "设备部", "investigator_ids": [str(investigator)], "dept_head_id": str(head)},
            {"department": "生产部", "investigator_ids": [], "dept_head_id": str(head)},
        ]
    )
    service, _db = _service(row)

    def _payload(department: str) -> CrossDeptInvestigationRequest:
        return CrossDeptInvestigationRequest(
            department=department,
            nonconformity_description="描述",
            root_cause_analysis="原因",
            risk_assessment="风险",
            capa_proposals=[CapaProposalItem(summary="整改")],
        )

    payload = _payload("设备部")

    with pytest.raises(ForbiddenException, match="调查人"):
        await service.submit_cross_dept_investigation(row.id, payload, actor_id=stranger, actor_name="路人")

    with pytest.raises(NotFoundException, match="跨部门行不存在"):
        await service.submit_cross_dept_investigation(
            row.id,
            _payload("工程部"),
            actor_id=investigator,
            actor_name="张三",
        )

    with pytest.raises(BadRequestException, match="未配置调查人"):
        await service.submit_cross_dept_investigation(
            row.id,
            _payload("生产部"),
            actor_id=head,
            actor_name="李四",
        )

    row.status = LedgerStatus.PENDING_QA_REVIEW.value
    with pytest.raises(BadRequestException, match="不在跨部门审核环节"):
        await service.submit_cross_dept_investigation(row.id, payload, actor_id=investigator, actor_name="张三")

    row.status = LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    row.cross_dept_reviewers = [
        {
            "department": "设备部",
            "investigator_ids": [str(investigator)],
            "dept_head_id": str(head),
            "review_state": CROSS_DEPT_ROW_APPROVED,
        }
    ]
    with pytest.raises(BadRequestException, match="已审核通过"):
        await service.submit_cross_dept_investigation(row.id, payload, actor_id=investigator, actor_name="张三")


async def test_submit_investigation_uses_transition_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """提交调查走 transition 时以「不符合事项描述」作为审核意见正文。"""
    investigator = uuid.uuid4()
    row = _row_ledger(status=LedgerStatus.PENDING_INVESTIGATION.value, handler_ids=[investigator])
    service, _db = _service(row)

    seen: dict[str, str] = {}

    async def fake_transition(db_arg: AsyncSession, **kwargs: Any) -> TransitionOutcome:
        seen["content"] = str(kwargs["content"])
        return TransitionOutcome(
            ledger=row,
            step="investigation",
            result=APPROVED,
            previous_status=row.status,
            next_status=row.status,
            skipped_steps=[],
            next_handlers=[],
            actor_name="调查人",
            directory=_directory(),
            handlers={},
        )

    monkeypatch.setattr(service_module, "transition", fake_transition)
    await service.submit_investigation(
        row.id,
        _investigation_payload(nonconformity_description=" 批压不足 "),
        actor_id=investigator,
        actor_name="调查人",
    )

    assert seen["content"] == "批压不足"
    assert len(row.investigation_records or []) == 1


async def test_submit_investigation_attachment_only_uses_fallback_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """附件路线提交：文本为空时审核意见正文回退为「以调查报告附件形式提交」。"""
    investigator = uuid.uuid4()
    row = _record_row(status=LedgerStatus.PENDING_INVESTIGATION.value, handler_ids=[investigator])
    file_id = uuid.UUID(str(row.attachments[0]["file_id"]))
    service, _db = _service(row)

    seen: dict[str, str] = {}

    async def fake_transition(db_arg: AsyncSession, **kwargs: Any) -> TransitionOutcome:
        seen["content"] = str(kwargs["content"])
        return TransitionOutcome(
            ledger=row,
            step="investigation",
            result=APPROVED,
            previous_status=row.status,
            next_status=row.status,
            skipped_steps=[],
            next_handlers=[],
            actor_name="调查人",
            directory=_directory(),
            handlers={},
        )

    monkeypatch.setattr(service_module, "transition", fake_transition)
    await service.submit_investigation(
        row.id,
        _investigation_payload(
            nonconformity_description="",
            root_cause_analysis="",
            risk_assessment="",
            capa_proposals=[],
            attachment_file_ids=[file_id],
        ),
        actor_id=investigator,
        actor_name="调查人",
    )

    assert seen["content"] == "以调查报告附件形式提交"
    record = (row.investigation_records or [])[0]
    assert record["nonconformity_description"] == ""
    assert record["capa_proposals"] == []
    assert record["attachments"][0]["file_id"] == str(file_id)


async def test_remove_attachment_blocked_when_referenced_by_record(monkeypatch: pytest.MonkeyPatch) -> None:
    investigator = uuid.uuid4()
    file_id = uuid.uuid4()
    monkeypatch.setattr(core_storage, "is_enabled", lambda: False)
    #: 删除窗口只在调查节点开放（提交后只能预览/下载），这里用待调查状态验证「已被记录引用」单独拦截
    row = _record_row(file_id=file_id, status=LedgerStatus.PENDING_INVESTIGATION.value, handler_ids=[investigator])
    row.investigation_records = [{"nonconformity_description": "x", "attachments": [{"file_id": str(file_id)}]}]
    service, _db = _service(row)

    with pytest.raises(BadRequestException, match="已被调查记录引用"):
        await service.remove_attachment(row.id, file_id, actor_id=investigator)
    assert len(row.attachments or []) == 1

    other = uuid.uuid4()
    row.investigation_records = [{"nonconformity_description": "x", "attachments": [{"file_id": str(other)}]}]
    await service.remove_attachment(row.id, file_id, actor_id=investigator)
    assert row.attachments == []
