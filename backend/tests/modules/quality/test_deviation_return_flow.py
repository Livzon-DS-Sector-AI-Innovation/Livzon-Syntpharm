"""偏差退回目标选择、跨部门行级退回与调查提交（不依赖真实数据库）。

覆盖本轮改造的后端口径：

- 退回目标由服务端计算：只含当前环节之前、本单适用且有处理人的人工环节；
- 退回直接落到目标环节的 pending 状态，``returned_step`` 记录目标，目标环节通过后清空；
- 退回到跨部门环节或其之前时，所有跨部门行重置为待审核（调查结果保留）；
- 跨部门单行退回只重置该部门的调查与审核，流程仍停留在跨部门环节；
- 调查提交支持「提交信息」并做「调查记录 / 调查报告附件」二选一校验。
"""

from __future__ import annotations

import uuid
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException
from app.modules.quality.qms import deviation_ledger_service as service_module
from app.modules.quality.qms.deviation_flow import (
    CROSS_DEPT_INVESTIGATION_PENDING,
    CROSS_DEPT_INVESTIGATION_SUBMITTED,
    CROSS_DEPT_ROW_APPROVED,
    CROSS_DEPT_ROW_PENDING,
    CROSS_DEPT_STEP,
    REJECTED,
    RESUBMITTED,
    FlowContext,
    HandlerDirectory,
    TransitionOutcome,
    approve_cross_dept_row,
    reject_cross_dept_row,
    reset_cross_dept_rows,
    returnable_steps,
    transition,
)
from app.modules.quality.qms.deviation_ledger_constants import LedgerStatus
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger
from app.modules.quality.qms.deviation_ledger_schemas import (
    CapaProposalItem,
    InvestigationRequest,
    InvestigationSubmitRequest,
)
from app.modules.quality.qms.deviation_ledger_service import _has_investigation_material
from tests.modules.quality.test_deviation_cross_dept_records import (
    _directory,
    _FlowDB,
    _patch_flow,
    _ref,
    _row,
    _row_ledger,
    _service,
)

# ── 退回目标计算（纯函数） ──────────────────────────────────────────────


def _context(*refs: Any, handlers: dict[str, list[uuid.UUID]] | None = None) -> FlowContext:
    directory = _directory(*refs)
    return FlowContext(contacts={}, directory=directory, handlers=handlers or {})


def test_returnable_steps_skips_ai_and_unhandled_steps() -> None:
    investigator = _ref("张三")
    dept_head = _ref("李四")
    qa = _ref("王五")
    ledger = _row_ledger(
        status=LedgerStatus.PENDING_QA_REVIEW.value,
        handler_ids=[str(investigator.id)],
        needs_cross_dept_review=False,
    )
    handlers = {
        "investigation": [investigator.id],
        "dept_head_review": [dept_head.id],
        "cross_dept_head_review": [],
        "qa_review": [qa.id],
    }

    steps = returnable_steps(ledger, "qa_review", handlers)

    # AI 分析不是人工退回点；跨部门未启用时也不作为目标
    assert steps == ["investigation", "dept_head_review"]


def test_returnable_steps_includes_cross_dept_when_applicable() -> None:
    investigator = _ref("张三")
    dept_head = _ref("李四")
    cross_head = _ref("赵六")
    qa = _ref("王五")
    ledger = _row_ledger(
        status=LedgerStatus.PENDING_QA_REVIEW.value,
        handler_ids=[str(investigator.id)],
        needs_cross_dept_review=True,
        cross_dept_reviewers=[_row("设备部", [], dept_head_id=str(cross_head.id))],
    )
    handlers = {
        "investigation": [investigator.id],
        "dept_head_review": [dept_head.id],
        "cross_dept_head_review": [cross_head.id],
        "qa_review": [qa.id],
    }

    assert returnable_steps(ledger, "qa_review", handlers) == [
        "investigation",
        "dept_head_review",
        CROSS_DEPT_STEP,
    ]


def test_returnable_steps_empty_for_first_step() -> None:
    investigator = _ref("张三")
    ledger = _row_ledger(status=LedgerStatus.PENDING_INVESTIGATION.value, handler_ids=[str(investigator.id)])

    assert returnable_steps(ledger, "investigation", {"investigation": [investigator.id]}) == []


# ── 整环节退回 ──────────────────────────────────────────────────────────


def _cross_ledger(**overrides: Any) -> tuple[DeviationLedger, dict[str, Any], FlowContext]:
    investigator = _ref("张三")
    dept_head = _ref("李四")
    cross_head = _ref("赵六")
    qa = _ref("王五")
    ledger = _row_ledger(
        status=LedgerStatus.PENDING_QA_REVIEW.value,
        handler_ids=[str(investigator.id)],
        needs_cross_dept_review=True,
        cross_dept_reviewers=[
            _row(
                "设备部",
                [],
                dept_head_id=str(cross_head.id),
                review_state=CROSS_DEPT_ROW_APPROVED,
                approved_by=str(cross_head.id),
                approved_name="赵六",
                approved_at="2026-11-12T08:00:00+00:00",
                opinion="同意",
                investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED,
            )
        ],
        **overrides,
    )
    handlers = {
        "investigation": [investigator.id],
        "dept_head_review": [dept_head.id],
        "cross_dept_head_review": [cross_head.id],
        "qa_review": [qa.id],
    }
    context = _context(investigator, dept_head, cross_head, qa, handlers=handlers)
    return ledger, {"qa": qa, "investigator": investigator, "cross_head": cross_head}, context


async def test_reject_defaults_to_previous_step(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, refs, context = _cross_ledger()
    _patch_flow(monkeypatch, ledger, context)
    db = _FlowDB()

    outcome = await transition(
        cast(AsyncSession, db),
        ledger_id=ledger.id,
        step="qa_review",
        result=REJECTED,
        content="跨部门结论与附件不一致，请复核",
        actor_id=refs["qa"].id,
        actor_name="王五",
    )

    assert outcome.next_status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    assert ledger.status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    assert ledger.returned_step == CROSS_DEPT_STEP
    assert db.commits == 1


def test_reject_to_cross_dept_resets_all_rows() -> None:
    ledger, _refs, _context_ = _cross_ledger()
    # 直接调用纯函数校验行重置口径：审核痕迹清空、调查结果保留
    rows = reset_cross_dept_rows(ledger.cross_dept_reviewers or [])

    assert rows[0]["review_state"] == CROSS_DEPT_ROW_PENDING
    assert rows[0]["approved_by"] is None
    assert rows[0]["approved_name"] is None
    assert rows[0]["approved_at"] is None
    assert rows[0]["opinion"] is None
    assert rows[0]["investigate_state"] == CROSS_DEPT_INVESTIGATION_SUBMITTED


async def test_reject_to_explicit_earlier_step(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, refs, context = _cross_ledger()
    _patch_flow(monkeypatch, ledger, context)

    outcome = await transition(
        cast(AsyncSession, _FlowDB()),
        ledger_id=ledger.id,
        step="qa_review",
        result=REJECTED,
        content="调查结论不充分",
        actor_id=refs["qa"].id,
        actor_name="王五",
        target_step="investigation",
    )

    assert outcome.next_status == LedgerStatus.PENDING_INVESTIGATION.value
    assert ledger.returned_step == "investigation"
    rows = ledger.cross_dept_reviewers or []
    assert rows[0]["review_state"] == CROSS_DEPT_ROW_PENDING


async def test_reject_target_must_be_predecessor(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, refs, context = _cross_ledger()
    _patch_flow(monkeypatch, ledger, context)

    with pytest.raises(BadRequestException, match="退回目标环节不合法"):
        await transition(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger.id,
            step="qa_review",
            result=REJECTED,
            content="想跳到未来环节",
            actor_id=refs["qa"].id,
            actor_name="王五",
            target_step="qa_head_review",
        )
    # 校验失败不留下意见与状态变更
    assert ledger.status == LedgerStatus.PENDING_QA_REVIEW.value
    assert ledger.review_opinions == []


async def test_approve_clears_returned_step(monkeypatch: pytest.MonkeyPatch) -> None:
    dept_head = _ref("李四")
    cross_head = _ref("赵六")
    qa = _ref("王五")
    ledger = _row_ledger(
        status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value,
        handler_ids=[],
        needs_cross_dept_review=True,
        returned_step=CROSS_DEPT_STEP,
        cross_dept_reviewers=[_row("设备部", [], dept_head_id=str(cross_head.id))],
    )
    handlers = {
        "investigation": [],
        "dept_head_review": [dept_head.id],
        "cross_dept_head_review": [cross_head.id],
        "qa_review": [qa.id],
    }
    _patch_flow(monkeypatch, ledger, _context(dept_head, cross_head, qa, handlers=handlers))

    outcome = await transition(
        cast(AsyncSession, _FlowDB()),
        ledger_id=ledger.id,
        step="dept_head_review",
        result="approved",
        content="同意",
        actor_id=dept_head.id,
        actor_name="李四",
    )

    assert outcome.next_status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    assert ledger.returned_step is None


async def test_enter_cross_dept_with_all_rows_approved_advances(monkeypatch: pytest.MonkeyPatch) -> None:
    """防御性兜底：进入跨部门时所有行已通过，直接前进到 QA 审核，避免无人可操作。"""
    dept_head = _ref("李四")
    cross_head = _ref("赵六")
    qa = _ref("王五")
    ledger = _row_ledger(
        status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value,
        needs_cross_dept_review=True,
        cross_dept_reviewers=[
            _row(
                "设备部",
                [],
                dept_head_id=str(cross_head.id),
                review_state=CROSS_DEPT_ROW_APPROVED,
                investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED,
            )
        ],
    )
    handlers = {
        "investigation": [],
        "dept_head_review": [dept_head.id],
        "cross_dept_head_review": [cross_head.id],
        "qa_review": [qa.id],
    }
    _patch_flow(monkeypatch, ledger, _context(dept_head, cross_head, qa, handlers=handlers))

    outcome = await transition(
        cast(AsyncSession, _FlowDB()),
        ledger_id=ledger.id,
        step="dept_head_review",
        result="approved",
        content="同意",
        actor_id=dept_head.id,
        actor_name="李四",
    )

    assert outcome.next_status == LedgerStatus.PENDING_QA_REVIEW.value
    assert CROSS_DEPT_STEP in outcome.skipped_steps


# ── 跨部门单行退回 ──────────────────────────────────────────────────────


def _row_ledger_for_reject() -> tuple[Any, dict[str, Any], FlowContext]:
    investigator_a = _ref("张三")
    investigator_b = _ref("钱七")
    head_a = _ref("李四")
    head_b = _ref("孙八")
    ledger = _row_ledger(
        status=LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        needs_cross_dept_review=True,
        cross_dept_reviewers=[
            _row(
                "设备部",
                [str(investigator_a.id)],
                dept_head_id=str(head_a.id),
                review_state=CROSS_DEPT_ROW_APPROVED,
                approved_by=str(head_a.id),
                approved_name="李四",
                approved_at="2026-11-12T08:00:00+00:00",
                opinion="同意",
                investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED,
            ),
            _row(
                "生产部",
                [str(investigator_b.id)],
                dept_head_id=str(head_b.id),
                investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED,
            ),
        ],
    )
    context = _context(investigator_a, investigator_b, head_a, head_b)
    return ledger, {"head_a": head_a, "head_b": head_b, "investigator_b": investigator_b}, context


async def test_reject_row_only_resets_that_department(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, refs, context = _row_ledger_for_reject()
    _patch_flow(monkeypatch, ledger, context)
    db = _FlowDB()

    outcome = await reject_cross_dept_row(
        cast(AsyncSession, db),
        ledger_id=ledger.id,
        department="生产部",
        content="调查缺少批次数据",
        actor_id=refs["head_b"].id,
        actor_name="孙八",
    )

    rows = {str(item["department"]): item for item in ledger.cross_dept_reviewers or []}
    assert rows["设备部"]["review_state"] == CROSS_DEPT_ROW_APPROVED
    assert rows["设备部"]["approved_name"] == "李四"
    assert rows["生产部"]["review_state"] == CROSS_DEPT_ROW_PENDING
    assert rows["生产部"]["investigate_state"] == CROSS_DEPT_INVESTIGATION_PENDING
    assert rows["生产部"]["investigate_submitted_by"] is None
    assert rows["生产部"]["approved_by"] is None
    assert rows["生产部"]["opinion"] == "调查缺少批次数据"
    # 流程仍停留在跨部门环节
    assert outcome.next_status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    assert ledger.status == LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value
    assert ledger.review_opinions[-1]["result"] == REJECTED
    assert "生产部" in ledger.review_opinions[-1]["step_label"]


async def test_reject_row_requires_row_reviewer(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, refs, context = _row_ledger_for_reject()
    _patch_flow(monkeypatch, ledger, context)

    with pytest.raises(ForbiddenException):
        await reject_cross_dept_row(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger.id,
            department="生产部",
            content="越权退回",
            actor_id=refs["head_a"].id,
            actor_name="李四",
        )


async def test_reject_row_requires_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, refs, context = _row_ledger_for_reject()
    _patch_flow(monkeypatch, ledger, context)

    with pytest.raises(BadRequestException, match="退回理由"):
        await reject_cross_dept_row(
            cast(AsyncSession, _FlowDB()),
            ledger_id=ledger.id,
            department="生产部",
            content="   ",
            actor_id=refs["head_b"].id,
            actor_name="孙八",
        )


async def test_reject_approved_row_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """已通过的行也支持退回重做（审核人复核后撤回），其它行不受影响。"""
    ledger, refs, context = _row_ledger_for_reject()
    _patch_flow(monkeypatch, ledger, context)

    await reject_cross_dept_row(
        cast(AsyncSession, _FlowDB()),
        ledger_id=ledger.id,
        department="设备部",
        content="复核发现证据不足",
        actor_id=refs["head_a"].id,
        actor_name="李四",
    )

    rows = {str(item["department"]): item for item in ledger.cross_dept_reviewers or []}
    assert rows["设备部"]["review_state"] == CROSS_DEPT_ROW_PENDING
    assert rows["设备部"]["approved_by"] is None
    assert rows["设备部"]["opinion"] == "复核发现证据不足"
    assert rows["生产部"].get("review_state") is None


async def test_last_row_approval_clears_returned_step(monkeypatch: pytest.MonkeyPatch) -> None:
    """整环节退回到跨部门后逐行重新通过，最后一行通过即消费退回标记。"""
    head_a = _ref("李四")
    head_b = _ref("孙八")
    qa = _ref("王五")
    ledger = _row_ledger(
        status=LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        needs_cross_dept_review=True,
        returned_step=CROSS_DEPT_STEP,
        cross_dept_reviewers=[
            _row(
                "设备部",
                [],
                dept_head_id=str(head_a.id),
                review_state=CROSS_DEPT_ROW_APPROVED,
                investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED,
            ),
            _row(
                "生产部",
                [],
                dept_head_id=str(head_b.id),
                investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED,
            ),
        ],
    )
    handlers = {
        "investigation": [],
        "dept_head_review": [],
        "cross_dept_head_review": [head_a.id, head_b.id],
        "qa_review": [qa.id],
    }
    _patch_flow(monkeypatch, ledger, _context(head_a, head_b, qa, handlers=handlers))

    outcome = await approve_cross_dept_row(
        cast(AsyncSession, _FlowDB()),
        ledger_id=ledger.id,
        department="生产部",
        content="同意",
        actor_id=head_b.id,
        actor_name="孙八",
    )

    assert outcome.next_status == LedgerStatus.PENDING_QA_REVIEW.value
    assert ledger.returned_step is None


async def test_legacy_resubmit_consumes_returned_step(monkeypatch: pytest.MonkeyPatch) -> None:
    """历史 returned 数据重新提交后清空退回标记，避免长期被「已退回」统计命中。"""
    dept_head = _ref("李四")
    ledger = _row_ledger(
        status=LedgerStatus.RETURNED.value,
        returned_step="dept_head_review",
        handler_ids=[],
    )
    handlers = {"dept_head_review": [dept_head.id]}
    _patch_flow(monkeypatch, ledger, _context(dept_head, handlers=handlers))

    outcome = await transition(
        cast(AsyncSession, _FlowDB()),
        ledger_id=ledger.id,
        step="dept_head_review",
        result=RESUBMITTED,
        content="已按要求补充",
        actor_id=ledger.reporter_id,
        actor_name="上报人",
    )

    assert outcome.next_status == LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value
    assert ledger.returned_step is None


# ── 调查提交：二选一校验与提交说明 ──────────────────────────────────────


def test_has_investigation_material_two_choice() -> None:
    empty = _row_ledger(status=LedgerStatus.PENDING_INVESTIGATION.value)
    assert _has_investigation_material(empty) is False

    with_text = _row_ledger(investigation_records=[{"nonconformity_description": "不符合事项", "department": None}])
    assert _has_investigation_material(with_text) is True

    with_attachments = _row_ledger(
        investigation_records=[
            {
                "nonconformity_description": "",
                "attachments": [{"file_id": str(uuid.uuid4()), "file_name": "报告.pdf"}],
            }
        ]
    )
    assert _has_investigation_material(with_attachments) is True

    # 跨部门行记录不算主流程材料
    cross_only = _row_ledger(investigation_records=[{"nonconformity_description": "设备异常", "department": "设备部"}])
    assert _has_investigation_material(cross_only) is False

    # 台账已有调查文档同样满足二选一
    ledger_attachment = _row_ledger(attachments=[{"file_id": str(uuid.uuid4()), "file_name": "报告.pdf"}])
    assert _has_investigation_material(ledger_attachment) is True


async def test_submit_for_review_requires_material(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _row_ledger(status=LedgerStatus.PENDING_INVESTIGATION.value)
    service, _ = _service(row)

    with pytest.raises(BadRequestException, match="调查记录或上传调查报告附件"):
        await service.submit_investigation_for_review(
            row.id,
            InvestigationSubmitRequest(content="补充说明"),
            actor_id=row.reporter_id,
            actor_name="上报人",
        )


async def test_submit_for_review_rejects_wrong_status(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _row_ledger(
        status=LedgerStatus.PENDING_QA_REVIEW.value,
        investigation_records=[{"nonconformity_description": "不符合事项"}],
    )
    service, _ = _service(row)

    with pytest.raises(BadRequestException, match="不在调查环节"):
        await service.submit_investigation_for_review(
            row.id,
            InvestigationSubmitRequest(),
            actor_id=row.reporter_id,
            actor_name="上报人",
        )


async def test_submit_for_review_passes_content_and_skips_new_record(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _row_ledger(
        status=LedgerStatus.PENDING_INVESTIGATION.value,
        investigation_records=[{"nonconformity_description": "不符合事项"}],
    )
    service, _ = _service(row)
    calls: list[tuple[str, str]] = []

    async def fake_transition(db: Any, **kwargs: Any) -> TransitionOutcome:
        calls.append((kwargs["step"], kwargs["content"]))
        return TransitionOutcome(
            ledger=row,
            step=kwargs["step"],
            result=kwargs["result"],
            previous_status=LedgerStatus.PENDING_INVESTIGATION.value,
            next_status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value,
            skipped_steps=[],
            next_handlers=[],
            actor_name=kwargs["actor_name"],
            directory=HandlerDirectory({}),
            handlers={},
        )

    monkeypatch.setattr(service_module, "transition", fake_transition)

    await service.submit_investigation_for_review(
        row.id,
        InvestigationSubmitRequest(content="已按退回意见补充"),
        actor_id=row.reporter_id,
        actor_name="上报人",
    )

    assert calls == [("investigation", "已按退回意见补充")]
    # 不新建调查记录
    assert len(row.investigation_records or []) == 1


async def test_submit_for_review_default_content(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _row_ledger(
        status=LedgerStatus.PENDING_INVESTIGATION.value,
        investigation_records=[{"nonconformity_description": "不符合事项"}],
    )
    service, _ = _service(row)
    contents: list[str] = []

    async def fake_transition(db: Any, **kwargs: Any) -> TransitionOutcome:
        contents.append(kwargs["content"])
        return TransitionOutcome(
            ledger=row,
            step=kwargs["step"],
            result=kwargs["result"],
            previous_status=row.status,
            next_status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value,
            skipped_steps=[],
            next_handlers=[],
            actor_name=kwargs["actor_name"],
            directory=HandlerDirectory({}),
            handlers={},
        )

    monkeypatch.setattr(service_module, "transition", fake_transition)

    await service.submit_investigation_for_review(
        row.id,
        InvestigationSubmitRequest(),
        actor_id=row.reporter_id,
        actor_name="上报人",
    )

    assert contents == [service_module._INVESTIGATION_SUBMIT_CONTENT]


async def test_submit_investigation_uses_submit_content(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _row_ledger(status=LedgerStatus.PENDING_INVESTIGATION.value, handler_ids=[])
    service, _ = _service(row)
    contents: list[str] = []

    async def fake_transition(db: Any, **kwargs: Any) -> TransitionOutcome:
        contents.append(kwargs["content"])
        return TransitionOutcome(
            ledger=row,
            step=kwargs["step"],
            result=kwargs["result"],
            previous_status=row.status,
            next_status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value,
            skipped_steps=[],
            next_handlers=[],
            actor_name=kwargs["actor_name"],
            directory=HandlerDirectory({}),
            handlers={},
        )

    monkeypatch.setattr(service_module, "transition", fake_transition)

    payload = InvestigationRequest(
        nonconformity_description="不符合事项",
        root_cause_analysis="根本原因",
        risk_assessment="风险评估",
        capa_proposals=[CapaProposalItem(summary="整改措施")],
        submit_content="请审核附件中的批次数据",
    )
    await service.submit_investigation(
        row.id,
        payload,
        actor_id=row.reporter_id,
        actor_name="上报人",
    )

    assert contents == ["请审核附件中的批次数据"]
