"""AI 分析保存与调查报告提交的流程口径（不依赖真实数据库）。

覆盖本轮改造：

- 保存 AI 分析只写库：状态不变、不写审核意见、不推进流程，可反复重新分析；
- 流程唯一切换点：待 AI 分析状态提交调查报告时先补齐 ai_analysis 环节，
  再走 investigation 提交到部门负责人审核；
- 待 AI 分析阶段调查人 / 上报人可维护调查文档与调查报告。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException
from app.core.llm import llm_client
from app.modules.quality.qms import deviation_ledger_service as service_module
from app.modules.quality.qms.deviation_flow import APPROVED, HandlerDirectory, TransitionOutcome
from app.modules.quality.qms.deviation_ledger_constants import LedgerStatus
from app.modules.quality.qms.deviation_ledger_schemas import (
    AiAnalysisData,
    CompleteAiAnalysisRequest,
)
from tests.modules.quality.test_deviation_cross_dept_records import (
    _investigation_payload,
    _row_ledger,
    _service,
)


def _payload() -> CompleteAiAnalysisRequest:
    return CompleteAiAnalysisRequest(
        ai_analysis=AiAnalysisData(
            description="偏差描述",
            reason="可能原因",
            risk_assessment="风险评估",
            capa_suggestion="CAPA 建议",
            model="default",
            generated_at=datetime.now(UTC),
        )
    )


async def test_save_ai_analysis_keeps_status_and_opinions() -> None:
    reporter = uuid.uuid4()
    row = _row_ledger(status=LedgerStatus.PENDING_AI_ANALYSIS.value, reporter_id=reporter)
    service, db = _service(row)

    detail = await service.save_ai_analysis(row.id, _payload(), actor_id=reporter, actor_name="上报人")

    assert str(detail.id) == str(row.id)
    assert row.status == LedgerStatus.PENDING_AI_ANALYSIS.value
    assert (row.ai_analysis or {}).get("capa_suggestion") == "CAPA 建议"
    assert row.review_opinions == []
    assert db.commits == 1


async def test_save_ai_analysis_rejects_unrelated_actor() -> None:
    """AI 结论与调查记录同口径：只有上报人 / 调查人 / 超管可保存。"""
    row = _row_ledger(status=LedgerStatus.PENDING_AI_ANALYSIS.value, reporter_id=uuid.uuid4())
    service, db = _service(row)

    with pytest.raises(ForbiddenException, match="AI 分析"):
        await service.save_ai_analysis(row.id, _payload(), actor_id=uuid.uuid4(), actor_name="路人")

    assert db.commits == 0


async def test_save_ai_analysis_allows_review_stage() -> None:
    """除已关闭 / 已取消外任意节点都可保存：审核阶段也允许覆盖旧结论。"""
    reporter = uuid.uuid4()
    row = _row_ledger(status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value, reporter_id=reporter)
    service, db = _service(row)

    await service.save_ai_analysis(row.id, _payload(), actor_id=reporter, actor_name="上报人")

    assert (row.ai_analysis or {}).get("description") == "偏差描述"
    assert db.commits == 1


async def test_save_ai_analysis_rejects_closed_and_cancelled() -> None:
    reporter = uuid.uuid4()
    for status in (LedgerStatus.CLOSED.value, LedgerStatus.CANCELLED.value):
        row = _row_ledger(status=status, reporter_id=reporter)
        service, db = _service(row)
        with pytest.raises(BadRequestException, match="AI 分析"):
            await service.save_ai_analysis(row.id, _payload(), actor_id=reporter, actor_name="上报人")
        assert db.commits == 0


async def test_generate_ai_analysis_available_at_review_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AI 分析不再局限待 AI 分析 / 已退回：审核阶段调查人也能重新分析。"""

    async def fake_chat_json(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "description": "AI 描述",
            "reason": "AI 原因",
            "risk_assessment": "AI 风险",
            "capa_suggestion": "AI CAPA",
        }

    monkeypatch.setattr(llm_client, "chat_json", fake_chat_json)
    investigator = uuid.uuid4()
    row = _row_ledger(status=LedgerStatus.PENDING_QA_REVIEW.value, handler_ids=[investigator])
    service, _db = _service(row)

    analysis = await service.generate_ai_analysis(row.id, actor_id=investigator)

    assert analysis.description == "AI 描述"
    assert analysis.model == "default"


async def test_generate_ai_analysis_rejects_stranger_and_closed() -> None:
    row = _row_ledger(status=LedgerStatus.PENDING_QA_REVIEW.value, handler_ids=[uuid.uuid4()])
    service, _db = _service(row)
    with pytest.raises(ForbiddenException, match="AI 分析"):
        await service.generate_ai_analysis(row.id, actor_id=uuid.uuid4())

    closed = _row_ledger(status=LedgerStatus.CLOSED.value)
    closed_service, _closed_db = _service(closed)
    with pytest.raises(BadRequestException, match="AI 分析"):
        await closed_service.generate_ai_analysis(closed.id, actor_id=uuid.uuid4(), actor_is_superuser=True)


async def test_save_ai_analysis_allows_superuser_any_stage() -> None:
    row = _row_ledger(status=LedgerStatus.PENDING_QA_REVIEW.value)
    service, _db = _service(row)

    await service.save_ai_analysis(
        row.id,
        _payload(),
        actor_id=uuid.uuid4(),
        actor_name="超管",
        actor_is_superuser=True,
    )

    assert (row.ai_analysis or {}).get("description") == "偏差描述"


async def test_submit_investigation_confirms_ai_analysis_first(monkeypatch: pytest.MonkeyPatch) -> None:
    investigator = uuid.uuid4()
    row = _row_ledger(status=LedgerStatus.PENDING_AI_ANALYSIS.value, handler_ids=[investigator])
    service, _db = _service(row)
    calls: list[tuple[str, str]] = []

    async def fake_transition(db_arg: AsyncSession, **kwargs: Any) -> TransitionOutcome:
        previous_status = row.status
        calls.append((str(kwargs["step"]), str(kwargs["content"])))
        if kwargs["step"] == "ai_analysis":
            row.status = LedgerStatus.PENDING_INVESTIGATION.value
        return TransitionOutcome(
            ledger=row,
            step=str(kwargs["step"]),
            result=APPROVED,
            previous_status=previous_status,
            next_status=row.status,
            skipped_steps=[],
            next_handlers=[],
            actor_name="调查人",
            directory=HandlerDirectory({}),
            handlers={},
        )

    monkeypatch.setattr(service_module, "transition", fake_transition)

    await service.submit_investigation(
        row.id,
        _investigation_payload(nonconformity_description=" 批压不足 "),
        actor_id=investigator,
        actor_name="调查人",
    )

    assert [step for step, _ in calls] == ["ai_analysis", "investigation"]
    assert "AI 分析" in calls[0][1]
    assert calls[1][1] == "批压不足"
    assert len(row.investigation_records or []) == 1


async def test_submit_investigation_validates_before_any_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    """附件校验失败时不能先提交 ai_analysis 环节，避免留下半提交状态。"""
    investigator = uuid.uuid4()
    row = _row_ledger(status=LedgerStatus.PENDING_AI_ANALYSIS.value, handler_ids=[investigator])
    service, db = _service(row)
    calls: list[str] = []

    async def fake_transition(db_arg: AsyncSession, **kwargs: Any) -> TransitionOutcome:
        calls.append(str(kwargs["step"]))
        raise AssertionError("校验失败时不应发生流转")

    monkeypatch.setattr(service_module, "transition", fake_transition)

    with pytest.raises(BadRequestException):
        await service.submit_investigation(
            row.id,
            _investigation_payload(attachment_file_ids=[uuid.uuid4()]),
            actor_id=investigator,
            actor_name="调查人",
        )

    assert calls == []
    assert db.commits == 0
    assert row.status == LedgerStatus.PENDING_AI_ANALYSIS.value
