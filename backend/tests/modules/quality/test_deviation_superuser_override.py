"""管理员代审口径：原因校验、意见标注与审计写入。

覆盖目标（B 口径「破窗代审」）：

- 超管代审必须填写原因（4~200 字），否则 400；
- 超管恰好是该环节处理人时不算代审，不需要原因；
- 代审意见带「【管理员代审】」前缀，并带结构化标记；
- 代审写 ``audit.logs``（``action=deviation.superuser_override``），与业务变更同事务。
"""

from __future__ import annotations

import uuid
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.modules.quality.qms import deviation_flow
from app.modules.quality.qms.deviation_flow import (
    OVERRIDE_AUDIT_ACTION,
    format_opinion_content,
    record_override_audit,
    resolve_override_reason,
)
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger


def _row() -> DeviationLedger:
    return DeviationLedger(
        id=uuid.uuid4(),
        code="PC20261113099",
        department="101车间",
        status="pending_qa_head_review",
        handler_ids=[],
        cross_dept_reviewers=[],
        reporter_id=uuid.uuid4(),
        review_opinions=[],
        investigation_records=[],
    )


def test_override_reason_required_for_superuser() -> None:
    with pytest.raises(BadRequestException) as excinfo:
        resolve_override_reason(uuid.uuid4(), {uuid.uuid4()}, actor_is_superuser=True, override_reason=None)
    assert "代审原因" in str(excinfo.value)


def test_override_reason_too_short_rejected() -> None:
    with pytest.raises(BadRequestException):
        resolve_override_reason(uuid.uuid4(), set(), actor_is_superuser=True, override_reason="ok")


def test_override_reason_too_long_rejected() -> None:
    with pytest.raises(BadRequestException):
        resolve_override_reason(uuid.uuid4(), set(), actor_is_superuser=True, override_reason="代" * 201)


def test_non_superuser_is_not_override() -> None:
    assert resolve_override_reason(uuid.uuid4(), set(), actor_is_superuser=False, override_reason="任意理由") is None


def test_superuser_as_handler_is_not_override() -> None:
    actor = uuid.uuid4()
    assert resolve_override_reason(actor, {actor}, actor_is_superuser=True, override_reason="理由充分") is None


def test_override_reason_is_trimmed() -> None:
    reason = resolve_override_reason(
        uuid.uuid4(), set(), actor_is_superuser=True, override_reason="  质量负责人休假  "
    )
    assert reason == "质量负责人休假"


def test_opinion_content_marks_override() -> None:
    assert format_opinion_content("同意", None) == "同意"
    assert format_opinion_content("同意", "质量负责人休假") == "【管理员代审】质量负责人休假｜同意"


async def test_record_override_audit_writes_action(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def _fake_record(db: Any, **kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(deviation_flow, "record_audit_log", _fake_record)
    row = _row()
    actor = uuid.uuid4()

    await record_override_audit(
        cast(AsyncSession, object()),
        ledger=row,
        step="qa_head_review",
        result="approved",
        actor_id=actor,
        reason="质量负责人休假",
        department="101车间",
    )

    assert captured["action"] == OVERRIDE_AUDIT_ACTION
    assert captured["user_id"] == actor
    assert captured["resource_type"] == "quality.deviation_ledger"
    assert captured["resource_id"] == row.id
    assert captured["new_value"]["override_reason"] == "质量负责人休假"
    assert captured["new_value"]["step"] == "qa_head_review"
