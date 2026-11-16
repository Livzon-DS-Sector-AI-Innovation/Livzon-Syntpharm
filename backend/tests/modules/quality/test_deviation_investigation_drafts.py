"""调查记录草稿与附件删除窗口（不依赖真实数据库）。

覆盖本轮改造的后端口径：

- 草稿按（作者, 部门）唯一覆盖，只能看到/清除本人草稿；
- 跨部门行草稿要求操作人是该行调查人且该行未通过；
- 提交调查（主流程 / 跨部门行）后草稿自动清除；
- 附件删除仅在调查节点、本人提交前开放，提交后只能预览与下载。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage as core_storage
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.modules.quality.qms import deviation_ledger_service as service_module
from app.modules.quality.qms.deviation_flow import (
    APPROVED,
    CROSS_DEPT_INVESTIGATION_PENDING,
    CROSS_DEPT_INVESTIGATION_SUBMITTED,
    HandlerDirectory,
    TransitionOutcome,
)
from app.modules.quality.qms.deviation_ledger_constants import LedgerStatus
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger
from app.modules.quality.qms.deviation_ledger_schemas import (
    CrossDeptInvestigationRequest,
    InvestigationDraftRequest,
    InvestigationRequest,
    LedgerDetail,
)
from app.modules.quality.qms.deviation_ledger_service import (
    DeviationLedgerService,
    _can_delete_attachment,
    _drop_investigation_draft,
)

# ── 公共构造器 ──────────────────────────────────────────────────────────


def _row_ledger(**overrides: Any) -> DeviationLedger:
    now = datetime.now(UTC)
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "code": "PC20261113001",
        "title": "偏差标题",
        "department": "101车间",
        "status": LedgerStatus.PENDING_INVESTIGATION.value,
        "status_updated_at": now,
        "reporter_id": uuid.uuid4(),
        "handler_ids": [],
        "needs_cross_dept_review": False,
        "cross_dept_reviewers": [],
        "review_opinions": [],
        "investigation_records": [],
        "investigation_drafts": [],
        "created_at": now,
        "updated_at": now,
        "is_deleted": False,
    }
    base.update(overrides)
    return DeviationLedger(**base)


class _Service(DeviationLedgerService):
    """草稿/权限测试不关心详情组装与通知：替换为无副作用实现。"""

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


class _NoopResult:
    rowcount = 0


class _ServiceDB:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: Any) -> None:
        return None

    async def execute(self, statement: Any) -> _NoopResult:
        return _NoopResult()


def _service(row: DeviationLedger | None) -> _Service:
    db = _ServiceDB()
    service = _Service(cast(AsyncSession, db))
    service.repo = cast(Any, _RowRepo(row))
    return service


def _draft(**overrides: Any) -> InvestigationDraftRequest:
    base: dict[str, Any] = {
        "nonconformity_description": "描述",
        "root_cause_analysis": "原因",
        "risk_assessment": "风险",
        "capa_proposals": [{"summary": "整改"}],
    }
    base.update(overrides)
    return InvestigationDraftRequest(**base)


def _cross_row(department: str, investigator: uuid.UUID, **state: Any) -> dict[str, Any]:
    return {
        "department": department,
        "investigator_ids": [str(investigator)],
        "dept_head_id": str(uuid.uuid4()),
        **state,
    }


# ── 草稿 schema ────────────────────────────────────────────────────────


def test_draft_request_allows_empty_and_normalizes() -> None:
    empty = InvestigationDraftRequest()
    assert empty.nonconformity_description == ""
    assert empty.capa_proposals == []
    assert empty.has_urgent is False

    file_id = uuid.uuid4()
    filled = InvestigationDraftRequest(
        nonconformity_description="  描述  ",
        urgent_measures="   ",
        attachment_file_ids=[file_id, file_id],
    )
    assert filled.nonconformity_description == "描述"
    assert filled.urgent_measures is None
    assert filled.attachment_file_ids == [file_id]

    with pytest.raises(ValueError, match="跨部门部门不能为空"):
        InvestigationDraftRequest(department="   ")


# ── 草稿读写 ───────────────────────────────────────────────────────────


async def test_save_draft_upserts_per_author_and_department() -> None:
    investigator = uuid.uuid4()
    other = uuid.uuid4()
    row = _row_ledger(handler_ids=[investigator, other])
    row.investigation_drafts = [
        {
            "author_id": str(other),
            "author_name": "另一调查人",
            "department": None,
            "nonconformity_description": "他的草稿",
        }
    ]
    service = _service(row)

    await service.save_investigation_draft(row.id, _draft(), actor_id=investigator, actor_name="张三")
    await service.save_investigation_draft(
        row.id, _draft(nonconformity_description="改过的描述"), actor_id=investigator, actor_name="张三"
    )

    drafts = row.investigation_drafts or []
    assert len(drafts) == 2
    mine = [entry for entry in drafts if entry["author_id"] == str(investigator)]
    assert len(mine) == 1
    assert mine[0]["nonconformity_description"] == "改过的描述"
    assert mine[0]["department"] is None
    assert mine[0]["capa_proposals"][0]["sequence"] == 1
    # 他人草稿不受影响
    assert [entry for entry in drafts if entry["author_id"] == str(other)][0]["nonconformity_description"] == "他的草稿"


async def test_cross_dept_draft_requires_row_investigator() -> None:
    investigator = uuid.uuid4()
    #: outsider 是可编辑调查文档的人（主调查人），但不是「设备部」这一行的调查人
    outsider = uuid.uuid4()
    row = _row_ledger(
        status=LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        needs_cross_dept_review=True,
        handler_ids=[investigator, outsider],
        cross_dept_reviewers=[_cross_row("设备部", investigator)],
    )
    service = _service(row)

    await service.save_investigation_draft(
        row.id, _draft(department="设备部"), actor_id=investigator, actor_name="张三"
    )
    assert len(row.investigation_drafts or []) == 1
    assert (row.investigation_drafts or [])[0]["department"] == "设备部"

    with pytest.raises(ForbiddenException, match="该部门的调查人"):
        await service.save_investigation_draft(
            row.id, _draft(department="设备部"), actor_id=outsider, actor_name="路人"
        )
    with pytest.raises(NotFoundException, match="跨部门行不存在"):
        await service.save_investigation_draft(
            row.id, _draft(department="生产部"), actor_id=investigator, actor_name="张三"
        )


async def test_cross_dept_draft_rejected_when_row_approved() -> None:
    investigator = uuid.uuid4()
    row = _row_ledger(
        status=LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        needs_cross_dept_review=True,
        handler_ids=[investigator],
        cross_dept_reviewers=[_cross_row("设备部", investigator, review_state="approved")],
    )
    service = _service(row)

    with pytest.raises(BadRequestException, match="已审核通过"):
        await service.save_investigation_draft(
            row.id, _draft(department="设备部"), actor_id=investigator, actor_name="张三"
        )


async def test_delete_draft_only_clears_own() -> None:
    investigator = uuid.uuid4()
    other = uuid.uuid4()
    row = _row_ledger(handler_ids=[investigator, other])
    row.investigation_drafts = [
        {"author_id": str(investigator), "department": None, "nonconformity_description": "我的"},
        {"author_id": str(other), "department": None, "nonconformity_description": "他的"},
    ]
    service = _service(row)

    await service.delete_investigation_draft(row.id, actor_id=investigator)

    drafts = row.investigation_drafts or []
    assert [entry["author_id"] for entry in drafts] == [str(other)]


# ── 提交后清草稿 ───────────────────────────────────────────────────────


async def test_submit_investigation_clears_own_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    investigator = uuid.uuid4()
    row = _row_ledger(handler_ids=[investigator])
    row.investigation_drafts = [{"author_id": str(investigator), "department": None, "nonconformity_description": "d"}]
    service = _service(row)

    async def fake_transition(db_arg: AsyncSession, **kwargs: Any) -> TransitionOutcome:
        return TransitionOutcome(
            ledger=row,
            step="investigation",
            result=APPROVED,
            previous_status=row.status,
            next_status=row.status,
            skipped_steps=[],
            next_handlers=[],
            actor_name="张三",
            directory=HandlerDirectory({}),
            handlers={},
        )

    monkeypatch.setattr(service_module, "transition", fake_transition)
    await service.submit_investigation(
        row.id,
        InvestigationRequest(
            nonconformity_description="描述",
            root_cause_analysis="原因",
            risk_assessment="风险",
            capa_proposals=[{"summary": "整改"}],
        ),
        actor_id=investigator,
        actor_name="张三",
    )

    assert row.investigation_drafts == []


async def test_cross_dept_submit_clears_row_draft_only() -> None:
    investigator = uuid.uuid4()
    row = _row_ledger(
        status=LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        needs_cross_dept_review=True,
        handler_ids=[investigator],
        cross_dept_reviewers=[_cross_row("设备部", investigator)],
    )
    row.investigation_drafts = [
        {"author_id": str(investigator), "department": "设备部", "nonconformity_description": "行草稿"},
        {"author_id": str(investigator), "department": None, "nonconformity_description": "主草稿"},
    ]
    service = _service(row)

    await service.submit_cross_dept_investigation(
        row.id,
        CrossDeptInvestigationRequest(
            department="设备部",
            nonconformity_description="描述",
            root_cause_analysis="原因",
            risk_assessment="风险",
            capa_proposals=[{"summary": "整改"}],
        ),
        actor_id=investigator,
        actor_name="张三",
    )

    drafts = row.investigation_drafts or []
    assert [entry["department"] for entry in drafts] == [None]


# ── 附件删除窗口 ───────────────────────────────────────────────────────


def test_can_delete_attachment_only_before_submit_at_investigation_stage() -> None:
    investigator = uuid.uuid4()
    investigation = _row_ledger(handler_ids=[investigator])
    assert _can_delete_attachment(investigation, investigator, False) is True
    assert _can_delete_attachment(investigation, uuid.uuid4(), False) is False
    assert _can_delete_attachment(investigation, None, False) is False

    review = _row_ledger(status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value, handler_ids=[investigator])
    assert _can_delete_attachment(review, investigator, False) is False
    assert _can_delete_attachment(review, investigator, True) is True

    returned = _row_ledger(
        status=LedgerStatus.RETURNED.value, returned_step="investigation", handler_ids=[investigator]
    )
    assert _can_delete_attachment(returned, investigator, False) is True


def test_can_delete_attachment_in_cross_dept_stage_until_row_submitted() -> None:
    investigator = uuid.uuid4()
    pending = _row_ledger(
        status=LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        cross_dept_reviewers=[_cross_row("设备部", investigator)],
    )
    assert _can_delete_attachment(pending, investigator, False) is True

    submitted = _row_ledger(
        status=LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        cross_dept_reviewers=[_cross_row("设备部", investigator, investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED)],
    )
    assert _can_delete_attachment(submitted, investigator, False) is False

    untouched = _row_ledger(
        status=LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
        cross_dept_reviewers=[
            _cross_row("设备部", investigator, investigate_state=CROSS_DEPT_INVESTIGATION_PENDING),
            _cross_row("生产部", uuid.uuid4(), investigate_state=CROSS_DEPT_INVESTIGATION_SUBMITTED),
        ],
    )
    assert _can_delete_attachment(untouched, investigator, False) is True


async def test_remove_attachment_rejected_after_submit() -> None:
    investigator = uuid.uuid4()
    file_id = uuid.uuid4()
    row = _row_ledger(
        status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value,
        handler_ids=[investigator],
        attachments=[{"file_id": str(file_id), "file_name": "a.pdf", "size": 1}],
    )
    service = _service(row)

    with pytest.raises(BadRequestException, match="只能预览与下载"):
        await service.remove_attachment(row.id, file_id, actor_id=investigator)
    assert len(row.attachments or []) == 1


async def test_remove_attachment_allowed_at_investigation_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    investigator = uuid.uuid4()
    file_id = uuid.uuid4()
    monkeypatch.setattr(core_storage, "is_enabled", lambda: False)
    row = _row_ledger(
        handler_ids=[investigator],
        attachments=[{"file_id": str(file_id), "file_name": "a.pdf", "size": 1}],
    )
    service = _service(row)

    await service.remove_attachment(row.id, file_id, actor_id=investigator)
    assert row.attachments == []


def test_drop_investigation_draft_matches_department_scope() -> None:
    author = uuid.uuid4()
    drafts: list[Any] = [
        {"author_id": str(author), "department": None},
        {"author_id": str(author), "department": "设备部"},
        {"author_id": str(uuid.uuid4()), "department": "设备部"},
        "脏数据",
    ]

    kept_main = _drop_investigation_draft(drafts, author, None)
    kept_row = _drop_investigation_draft(drafts, author, "设备部")
    assert [entry.get("department") for entry in kept_main] == [
        "设备部",
        "设备部",
    ]
    assert [entry.get("department") for entry in kept_row] == [
        None,
        "设备部",
    ]
