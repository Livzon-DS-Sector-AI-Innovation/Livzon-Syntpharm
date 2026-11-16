"""偏差审核权限与调查补录权限（纯函数 / 无数据库）。

覆盖三处口径：

- 非超管必须严格是当前环节处理人，``approved`` / ``rejected`` / ``resubmitted`` 一律校验；
- 环节未配置处理人时拒绝普通用户，并提示去部门联系人配置；
- 调查记录 / 文档的编辑能力覆盖待 AI 分析、调查中与全部审核环节，限调查人与上报人。
"""

from __future__ import annotations

import uuid
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException
from app.modules.quality.qms.deviation_flow import (
    FlowContext,
    HandlerDirectory,
    ensure_actor_allowed,
)
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger
from app.modules.quality.qms.deviation_ledger_service import (
    DeviationLedgerService,
    _allowed_actions,
)


def _flow(handlers: dict[str, list[uuid.UUID]] | None = None) -> FlowContext:
    return FlowContext(contacts={}, directory=HandlerDirectory({}), handlers=handlers or {})


def _row(**overrides: object) -> DeviationLedger:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "code": "PC20261112001",
        "department": "101车间",
        "status": "pending_dept_head_review",
        "handler_ids": [],
        "cross_dept_reviewers": [],
        "reporter_id": uuid.uuid4(),
        "review_opinions": [],
        "investigation_records": [],
    }
    values.update(overrides)
    row = DeviationLedger(**values)
    return row


def _service() -> DeviationLedgerService:
    return DeviationLedgerService(cast(AsyncSession, object()))


# ── ensure_actor_allowed ────────────────────────────────────────────────


def test_actor_in_allowed_passes() -> None:
    actor = uuid.uuid4()
    ensure_actor_allowed("dept_head_review", {actor}, actor, actor_is_superuser=False)


def test_superuser_override_requires_reason() -> None:
    with pytest.raises(BadRequestException) as excinfo:
        ensure_actor_allowed("dept_head_review", set(), uuid.uuid4(), actor_is_superuser=True)
    assert "代审原因" in str(excinfo.value)


def test_superuser_override_returns_reason() -> None:
    reason = ensure_actor_allowed(
        "dept_head_review",
        {uuid.uuid4()},
        uuid.uuid4(),
        actor_is_superuser=True,
        override_reason="  质量负责人休假，管理者代审  ",
    )
    assert reason == "质量负责人休假，管理者代审"


def test_superuser_override_reason_too_short() -> None:
    with pytest.raises(BadRequestException):
        ensure_actor_allowed("dept_head_review", set(), uuid.uuid4(), actor_is_superuser=True, override_reason="ok")


def test_superuser_override_reason_too_long() -> None:
    with pytest.raises(BadRequestException):
        ensure_actor_allowed(
            "dept_head_review", set(), uuid.uuid4(), actor_is_superuser=True, override_reason="代" * 201
        )


def test_superuser_as_handler_needs_no_reason() -> None:
    actor = uuid.uuid4()
    assert ensure_actor_allowed("dept_head_review", {actor}, actor, actor_is_superuser=True) is None


def test_actor_not_in_allowed_is_forbidden() -> None:
    with pytest.raises(ForbiddenException) as excinfo:
        ensure_actor_allowed("dept_head_review", {uuid.uuid4()}, uuid.uuid4(), actor_is_superuser=False)
    assert "无权操作" in str(excinfo.value)


def test_empty_handlers_rejects_and_points_to_config() -> None:
    with pytest.raises(ForbiddenException) as excinfo:
        ensure_actor_allowed("qa_review", set(), uuid.uuid4(), actor_is_superuser=False)
    assert "部门联系人配置" in str(excinfo.value)


# ── _allowed_actions ────────────────────────────────────────────────────


def test_review_actions_only_for_step_handler() -> None:
    handler = uuid.uuid4()
    flow = _flow({"dept_head_review": [handler]})
    row = _row()

    assert _allowed_actions(row, "dept_head_review", flow, viewer_id=handler, viewer_is_superuser=False) == [
        "approve",
        "reject",
    ]
    stranger = uuid.uuid4()
    assert _allowed_actions(row, "dept_head_review", flow, viewer_id=stranger, viewer_is_superuser=False) == []


def test_review_actions_for_superuser_kept() -> None:
    flow = _flow({"dept_head_review": [uuid.uuid4()]})
    actions = _allowed_actions(_row(), "dept_head_review", flow, viewer_id=uuid.uuid4(), viewer_is_superuser=True)
    assert "approve" in actions and "reject" in actions


def test_returned_actions_limited_to_reporter_and_investigator() -> None:
    reporter = uuid.uuid4()
    investigator = uuid.uuid4()
    row = _row(status="returned", returned_step="investigation", reporter_id=reporter, handler_ids=[investigator])
    flow = _flow()

    assert _allowed_actions(row, "investigation", flow, viewer_id=reporter, viewer_is_superuser=False) == [
        "resubmit",
        "edit",
        "analyze",
    ]
    assert _allowed_actions(row, "investigation", flow, viewer_id=investigator, viewer_is_superuser=False) == [
        "resubmit",
        "edit",
        "analyze",
    ]
    assert _allowed_actions(row, "investigation", flow, viewer_id=uuid.uuid4(), viewer_is_superuser=False) == []


def test_ai_analysis_actions_allow_investigation_for_investigator() -> None:
    """AI 分析只保存不流转，调查报告的提交才是流程入口，故调查人 / 上报人此时可调查。"""
    reporter = uuid.uuid4()
    investigator = uuid.uuid4()
    row = _row(status="pending_ai_analysis", reporter_id=reporter, handler_ids=[investigator])
    flow = _flow({"investigation": [investigator]})

    assert _allowed_actions(row, "ai_analysis", flow, viewer_id=reporter, viewer_is_superuser=False) == [
        "investigate",
        "analyze",
    ]
    assert _allowed_actions(row, "ai_analysis", flow, viewer_id=investigator, viewer_is_superuser=False) == [
        "investigate",
        "analyze",
    ]
    # 与分析结论的编辑范围一致：无关用户既不能分析也不能调查
    assert _allowed_actions(row, "ai_analysis", flow, viewer_id=uuid.uuid4(), viewer_is_superuser=False) == []


# ── 调查记录 / 文档编辑权限 ─────────────────────────────────────────────


def test_investigator_can_edit_attachments_during_review() -> None:
    investigator = uuid.uuid4()
    row = _row(status="pending_qa_review", handler_ids=[investigator])
    _service()._assert_can_edit_investigation(row, investigator)


def test_reporter_can_edit_attachments_after_return() -> None:
    reporter = uuid.uuid4()
    row = _row(status="returned", returned_step="qa_review", reporter_id=reporter)
    _service()._assert_can_edit_investigation(row, reporter)


def test_stranger_cannot_edit_attachments() -> None:
    row = _row(status="pending_qa_review", handler_ids=[uuid.uuid4()])
    with pytest.raises(ForbiddenException):
        _service()._assert_can_edit_investigation(row, uuid.uuid4())


def test_attachments_editable_while_ai_analysis_pending() -> None:
    """调查报告在待 AI 分析阶段填写，调查人 / 上报人此时即可维护调查文档。"""
    reporter = uuid.uuid4()
    investigator = uuid.uuid4()
    row = _row(status="pending_ai_analysis", reporter_id=reporter, handler_ids=[investigator])
    service = _service()

    service._assert_can_edit_investigation(row, reporter)
    service._assert_can_edit_investigation(row, investigator)


def test_attachments_locked_before_investigation() -> None:
    reporter = uuid.uuid4()
    row = _row(status="pending_final_code", reporter_id=reporter)
    with pytest.raises(BadRequestException):
        _service()._assert_can_edit_investigation(row, reporter)


# ── AI 分析全节点可用 ───────────────────────────────────────────────────


def test_analyze_action_available_at_review_and_final_code() -> None:
    """除已关闭 / 已取消外任意节点都保留 AI 分析入口（人员仍限上报人 / 调查人 / 超管）。"""
    investigator = uuid.uuid4()
    flow = _flow()
    for status, step in (("pending_qa_review", "qa_review"), ("pending_final_code", "final_code")):
        row = _row(status=status, handler_ids=[investigator])
        assert "analyze" in _allowed_actions(row, step, flow, viewer_id=investigator, viewer_is_superuser=False)
    stranger_row = _row(status="pending_qa_review", handler_ids=[investigator])
    assert _allowed_actions(stranger_row, "qa_review", flow, viewer_id=uuid.uuid4(), viewer_is_superuser=False) == []


def test_analyze_action_absent_for_closed_and_cancelled() -> None:
    reporter = uuid.uuid4()
    flow = _flow()
    for status in ("closed", "cancelled"):
        row = _row(status=status, reporter_id=reporter)
        assert "analyze" not in _allowed_actions(row, None, flow, viewer_id=reporter, viewer_is_superuser=False)
