"""首页工作台聚合逻辑单测（不连库）。

覆盖：偏差当前环节口径（含 returned_step）、超期判定、隐患复核级别推导、
分组顺序与降级、无模块权限时数据源整体跳过。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.quality.qms.deviation_ledger_constants import LedgerStatus
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger
from app.modules.quality.qms.workbench_query import _deviation_item, _deviation_step
from app.modules.safety.models import HazardReport
from app.modules.safety.service.hazard_workbench import _pending_review_level
from app.platform.identity.models import User
from app.platform.workbench import service as workbench_service
from app.platform.workbench.constants import MATCH_PERSON, MATCH_ROLE
from app.shared.workbench_types import WorkbenchItem, WorkbenchSourceResult

_UID = uuid.uuid4()


def _ledger(**overrides: object) -> DeviationLedger:
    values: dict[str, object] = {
        "code": "PC20260101001",
        "title": "投料量偏差",
        "department": "生产部",
        "discovery_date": datetime.now(UTC).date(),
        "discovery_location": "一车间",
        "discoverer_id": _UID,
        "affected_items": "样品 A",
        "batch_number": "B001",
        "description": "描述",
        "reporter_id": _UID,
        "status": LedgerStatus.PENDING_QA_REVIEW.value,
        "status_updated_at": datetime.now(UTC),
        "handler_ids": [],
        "cross_dept_reviewers": [],
        "review_opinions": [],
    }
    values.update(overrides)
    return DeviationLedger(**values)


def _hazard(**overrides: object) -> HazardReport:
    values: dict[str, object] = {
        "hazard_no": "HZ-0001",
        "hazard_type": "物的不安全状态",
        "hazard_level": "serious",
        "description": "护栏缺失",
        "discovered_at": datetime.now(UTC),
        "status": "open",
        "rectification_status": "replied",
        "ai_review_status": "completed",
        "verify_level_1_status": "pending",
        "verify_level_2_status": "pending",
        "verify_level_3_status": "pending",
    }
    values.update(overrides)
    return HazardReport(**values)


def _item(module_key: str, *, overdue: bool = False, age: int = 1) -> WorkbenchItem:
    return WorkbenchItem(
        id=str(uuid.uuid4()),
        source="deviation" if module_key == "quality" else "hazard",
        module_key=module_key,
        module_label="质量管理" if module_key == "quality" else "安全管理",
        doc_type_label="单据",
        title="t",
        match_kind=MATCH_PERSON,
        age_days=age,
        overdue=overdue,
    )


# ── 偏差：当前环节与超期 ──────────────────────────────────────────


def test_deviation_step_falls_back_to_status_mapping() -> None:
    row = _ledger(status=LedgerStatus.PENDING_INVESTIGATION.value)
    assert _deviation_step(row) == "investigation"


def test_deviation_step_prefers_returned_step_for_returned_status() -> None:
    row = _ledger(status=LedgerStatus.RETURNED.value, returned_step="qa_review")
    assert _deviation_step(row) == "qa_review"
    item = _deviation_item(row, step="qa_review", match_kind=MATCH_PERSON)
    assert item.step_label == "所属QA审核（已退回）"


def test_deviation_item_marks_overdue_by_status_threshold() -> None:
    row = _ledger(
        status=LedgerStatus.PENDING_QA_REVIEW.value,
        status_updated_at=datetime.now(UTC) - timedelta(days=6),
    )
    item = _deviation_item(row, step="qa_review", match_kind=MATCH_ROLE)
    assert item.age_days == 6
    # 所属QA审核阈值为 5 天
    assert item.overdue is True
    assert item.path == f"/quality/deviation/{row.id}"


# ── 隐患：复核级别推导 ────────────────────────────────────────────


def test_hazard_pending_level_one_requires_ai_completed() -> None:
    assert _pending_review_level(_hazard()) == 1
    assert _pending_review_level(_hazard(ai_review_status="processing")) is None


def test_hazard_pending_level_two_after_level_one_approved() -> None:
    row = _hazard(rectification_status="level1_approved", verify_level_1_status="approved")
    assert _pending_review_level(row) == 2


def test_hazard_pending_level_three_with_no_review_needed() -> None:
    row = _hazard(
        rectification_status="level2_approved",
        verify_level_1_status="approved",
        verify_level_2_status="no_review_needed",
    )
    assert _pending_review_level(row) == 3


def test_hazard_closed_when_all_levels_approved() -> None:
    row = _hazard(
        verify_level_1_status="approved",
        verify_level_2_status="approved",
        verify_level_3_status="approved",
    )
    assert _pending_review_level(row) is None


# ── 分组与降级 ────────────────────────────────────────────────────


def test_group_orders_quality_before_safety() -> None:
    groups = workbench_service._group([_item("safety"), _item("quality")], {})
    assert [group.module_key for group in groups] == ["quality", "safety"]
    assert groups[0].items[0].match_kind_label == "待我审批"


def test_group_skips_modules_without_items() -> None:
    groups = workbench_service._group([_item("quality")], {"quality": True})
    assert len(groups) == 1
    assert groups[0].has_more is True


def test_todo_sort_puts_overdue_first_then_older() -> None:
    overdue = _item("quality", overdue=True, age=9)
    old = _item("quality", overdue=False, age=8)
    fresh = _item("quality", overdue=False, age=1)
    ordered = sorted([fresh, old, overdue], key=workbench_service._todo_sort_key)
    assert ordered == [overdue, old, fresh]


async def test_collect_degrades_single_source_on_error() -> None:
    async def _boom() -> WorkbenchSourceResult:
        raise RuntimeError("db down")

    degraded: list[str] = []
    result = await workbench_service._collect("quality.deviation.todos", _boom(), degraded)
    assert result.items == []
    assert result.has_more is False
    assert degraded == ["quality.deviation.todos"]


# ── 平台层：权限门控 ──────────────────────────────────────────────


async def test_build_overview_without_permissions_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _codes(_db: object, _user: object) -> set[str]:
        return set()

    async def _empty(_db: object, **kwargs: object) -> WorkbenchSourceResult:
        # 平台层只负责把权限码下发给各源，判定由各源自己完成
        assert kwargs.get("granted") == set()
        return WorkbenchSourceResult()

    monkeypatch.setattr(workbench_service, "effective_permission_codes", _codes)
    for name in (
        "list_deviation_todos",
        "list_inspection_todos",
        "list_capa_todos",
        "list_deviation_processes",
        "list_inspection_processes",
        "list_hazard_review_todos",
        "list_hazard_processes",
    ):
        monkeypatch.setattr(workbench_service, name, _empty)

    user = User(id=_UID, name="张三", employee_no="E001")
    data = await workbench_service.build_overview(None, user, todo_limit=5, process_limit=5)  # type: ignore[arg-type]

    assert data.todos.total == 0
    assert data.processes.total == 0
    assert data.todos.groups == []
    assert data.degraded_sources == []


async def test_build_overview_counts_and_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _codes(_db: object, _user: object) -> set[str]:
        return {"quality:deviation:read", "quality:deviation:approve", "safety:hazard:manage"}

    async def _deviation_todos(_db: object, **_kwargs: object) -> WorkbenchSourceResult:
        return WorkbenchSourceResult(
            items=[
                WorkbenchItem(
                    id="1",
                    source="deviation",
                    module_key="quality",
                    module_label="质量管理",
                    doc_type_label="偏差台账",
                    title="A",
                    match_kind=MATCH_PERSON,
                ),
                WorkbenchItem(
                    id="2",
                    source="deviation",
                    module_key="quality",
                    module_label="质量管理",
                    doc_type_label="偏差台账",
                    title="B",
                    match_kind=MATCH_ROLE,
                ),
            ],
            has_more=True,
        )

    async def _empty(_db: object, **_kwargs: object) -> WorkbenchSourceResult:
        return WorkbenchSourceResult()

    monkeypatch.setattr(workbench_service, "effective_permission_codes", _codes)
    monkeypatch.setattr(workbench_service, "list_deviation_todos", _deviation_todos)
    monkeypatch.setattr(workbench_service, "list_inspection_todos", _empty)
    monkeypatch.setattr(workbench_service, "list_capa_todos", _empty)
    monkeypatch.setattr(workbench_service, "list_deviation_processes", _empty)
    monkeypatch.setattr(workbench_service, "list_inspection_processes", _empty)
    monkeypatch.setattr(workbench_service, "list_hazard_review_todos", _empty)
    monkeypatch.setattr(workbench_service, "list_hazard_processes", _empty)

    async def _no_reads(_db: object, _user_id: object, _sources: object) -> dict[tuple[str, str], str]:
        return {}

    monkeypatch.setattr(workbench_service, "load_read_fingerprints", _no_reads)

    user = User(id=_UID, name="张三", employee_no="E001")
    data = await workbench_service.build_overview(None, user, todo_limit=5, process_limit=5)  # type: ignore[arg-type]

    assert data.todos.total == 2
    assert data.todos.unread_total == 2
    assert data.todos.person_total == 1
    assert data.todos.role_total == 1
    assert data.todos.has_more is True
    assert data.todos.groups[0].count == 2
    assert all(item.is_read is False for item in data.todos.groups[0].items or [])


async def test_build_overview_marks_read_items_by_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    """指纹一致才算已读：一条已读、一条环节变化后重新未读。"""

    async def _codes(_db: object, _user: object) -> set[str]:
        return {"quality:deviation:read", "quality:deviation:approve"}

    def _todo(item_id: str, step: str | None) -> WorkbenchItem:
        return WorkbenchItem(
            id=item_id,
            source="deviation",
            module_key="quality",
            module_label="质量管理",
            doc_type_label="偏差台账",
            title=item_id,
            status="pending",
            step_label=step,
            match_kind=MATCH_PERSON,
        )

    async def _deviation_todos(_db: object, **_kwargs: object) -> WorkbenchSourceResult:
        return WorkbenchSourceResult(items=[_todo("1", "QA 审核"), _todo("2", "QC 审核")])

    async def _empty(_db: object, **_kwargs: object) -> WorkbenchSourceResult:
        return WorkbenchSourceResult()

    # item 1 的已读指纹与当前一致；item 2 停在旧环节（指纹不同）→ 应重新提醒
    async def _reads(_db: object, _user_id: object, _sources: object) -> dict[tuple[str, str], str]:
        return {("deviation", "1"): "pending|QA 审核|person", ("deviation", "2"): "pending|QA 审核|person"}

    monkeypatch.setattr(workbench_service, "effective_permission_codes", _codes)
    monkeypatch.setattr(workbench_service, "list_deviation_todos", _deviation_todos)
    monkeypatch.setattr(workbench_service, "list_inspection_todos", _empty)
    monkeypatch.setattr(workbench_service, "list_capa_todos", _empty)
    monkeypatch.setattr(workbench_service, "list_deviation_processes", _empty)
    monkeypatch.setattr(workbench_service, "list_inspection_processes", _empty)
    monkeypatch.setattr(workbench_service, "list_hazard_review_todos", _empty)
    monkeypatch.setattr(workbench_service, "list_hazard_processes", _empty)
    monkeypatch.setattr(workbench_service, "load_read_fingerprints", _reads)

    user = User(id=_UID, name="张三", employee_no="E001")
    data = await workbench_service.build_overview(None, user, todo_limit=5, process_limit=5)  # type: ignore[arg-type]

    items = {item.id: item for group in data.todos.groups for item in group.items or []}
    assert items["1"].is_read is True
    assert items["2"].is_read is False
    assert data.todos.unread_total == 1
