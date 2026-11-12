"""Org department sync seam (ticket #197).

Seam: ``sync_org_departments(store, fetcher)`` with an in-memory store and fake
Feishu fetchers. Catches:
- upsert of every in-scope department with directory detail fields;
- stale/removed departments flagged hidden, never deleted;
- out-of-scope mirror rows left untouched;
- detail-less / empty-field departments still upserted with empty values;
- level > 2 departments ignored.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from app.modules.hr.org_domain import (
    IN_SCOPE_COMPANY_ID,
    IN_SCOPE_COMPANY_NAME,
    OrgDepartmentRecord,
)
from app.modules.hr.org_sync import OrgSyncStats, SyncRunRecord, sync_org_departments


class FakeFetcher:
    def __init__(
        self,
        *,
        departments: list[dict[str, Any]],
        details: list[dict[str, Any]],
    ) -> None:
        self.departments = departments
        self.details = details
        self.detail_requests: list[list[str]] = []

    async def fetch_departments(self) -> list[dict[str, Any]]:
        return self.departments

    async def fetch_departments_detail(self, department_ids: list[str]) -> list[dict[str, Any]]:
        self.detail_requests.append(list(department_ids))
        requested = set(department_ids)
        return [detail for detail in self.details if detail.get("department_id") in requested]


class FakeStore:
    def __init__(self, existing: list[OrgDepartmentRecord] | None = None) -> None:
        self.records: dict[str, OrgDepartmentRecord] = {r.id: r for r in existing or [] if r.id}
        self._initial = copy.deepcopy(self.records)
        self.hidden: list[str] = []
        self.runs: list[SyncRunRecord] = []

    async def list_departments(self) -> list[OrgDepartmentRecord]:
        return list(self.records.values())

    async def upsert_department(self, record: OrgDepartmentRecord) -> bool:
        assert record.id
        created = record.id not in self.records
        self.records[record.id] = record
        return created

    async def hide_department(self, department_id: str) -> None:
        self.hidden.append(department_id)
        if department_id in self.records:
            self.records[department_id].hidden = True

    async def record_sync_run(self, run: SyncRunRecord, *, run_id: UUID | None = None) -> None:
        self.runs.append(run)

    async def rollback(self) -> None:
        self.records = copy.deepcopy(self._initial)
        self.hidden = []


def _contact(dept_id: str, name: str, parent_id: str) -> dict[str, Any]:
    return {"department_id": dept_id, "name": name, "parent_department_id": parent_id}


def _detail(
    dept_id: str,
    name: str,
    parent_id: str,
    *,
    leaders: list[str] | None = None,
    path: list[dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "department_id": dept_id,
        "name": {"default_value": name},
        "parent_department_id": parent_id,
        "enabled_status": True,
        "order_weight": "10",
        "leaders": [{"leader_id": leader_id} for leader_id in leaders or []],
        "department_count": {
            "recursive_members_count": "42",
            "direct_members_count": "12",
            "recursive_departments_count": "3",
            "direct_departments_count": "2",
        },
        "department_path_infos": path
        or [
            {"department_id": IN_SCOPE_COMPANY_ID, "department_name": {"default_value": IN_SCOPE_COMPANY_NAME}},
            {"department_id": dept_id, "department_name": {"default_value": name}},
        ],
        "data_source": 1,
        "custom_field_values": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_sync_upserts_tree_and_directory_fields() -> None:
    fetcher = FakeFetcher(
        departments=[
            _contact("od-101", "101车间", IN_SCOPE_COMPANY_ID),
            _contact("od-101-1", "合成工段", "od-101"),
        ],
        details=[
            _detail("od-101", "101车间", IN_SCOPE_COMPANY_ID, leaders=["ou-leader"]),
            _detail(
                "od-101-1",
                "合成工段",
                "od-101",
                path=[
                    {"department_id": IN_SCOPE_COMPANY_ID, "department_name": {"default_value": IN_SCOPE_COMPANY_NAME}},
                    {"department_id": "od-101", "department_name": {"default_value": "101车间"}},
                    {"department_id": "od-101-1", "department_name": {"default_value": "合成工段"}},
                ],
            ),
        ],
    )
    store = FakeStore()

    stats = await sync_org_departments(store, fetcher)

    assert stats == OrgSyncStats(total=2, created=2, updated=0, hidden=0)
    parent = store.records["od-101"]
    child = store.records["od-101-1"]
    assert parent.name == "101车间"
    assert parent.leader_ids == ["ou-leader"]
    assert parent.recursive_members_count == 42
    assert parent.direct_departments_count == 2
    assert parent.enabled_status is True
    assert parent.order_weight == "10"
    assert parent.order == 10
    assert parent.data_source == 1
    assert child.department_path[-1] == {"id": "od-101-1", "name": "合成工段"}
    assert fetcher.detail_requests == [["od-101", "od-101-1"]]


@pytest.mark.asyncio
async def test_sync_hides_removed_and_out_of_scope_rows() -> None:
    stale = OrgDepartmentRecord(
        id="od-stale",
        name="已移除车间",
        parent_id=IN_SCOPE_COMPANY_ID,
        department_path=[
            {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
            {"id": "od-stale", "name": "已移除车间"},
        ],
    )
    outside = OrgDepartmentRecord(
        id="od-trade",
        name="贸易一部",
        parent_id="od-other-company",
        department_path=[
            {"id": "od-other-company", "name": "珠海市丽珠医药贸易有限公司"},
            {"id": "od-trade", "name": "贸易一部"},
        ],
    )
    store = FakeStore(existing=[stale, outside])
    fetcher = FakeFetcher(
        departments=[_contact("od-101", "101车间", IN_SCOPE_COMPANY_ID)],
        details=[_detail("od-101", "101车间", IN_SCOPE_COMPANY_ID)],
    )

    stats = await sync_org_departments(store, fetcher)

    assert stats.hidden == 2
    assert store.hidden == ["od-stale", "od-trade"]
    assert store.records["od-trade"].hidden is True


@pytest.mark.asyncio
async def test_sync_upserts_department_when_directory_detail_is_missing() -> None:
    fetcher = FakeFetcher(
        departments=[_contact("od-101", "101车间", IN_SCOPE_COMPANY_ID)],
        details=[],
    )
    store = FakeStore()

    stats = await sync_org_departments(store, fetcher)

    assert stats.total == 1
    record = store.records["od-101"]
    assert record.name == "101车间"
    assert record.leader_ids == []
    assert record.department_path == [
        {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
        {"id": "od-101", "name": "101车间"},
    ]
    assert record.enabled_status is None
    assert record.recursive_members_count == 0


@pytest.mark.asyncio
async def test_sync_ignores_departments_deeper_than_two_levels() -> None:
    fetcher = FakeFetcher(
        departments=[
            _contact("od-101", "101车间", IN_SCOPE_COMPANY_ID),
            _contact("od-101-1", "合成工段", "od-101"),
            _contact("od-101-1-1", "班组", "od-101-1"),
        ],
        details=[
            _detail("od-101", "101车间", IN_SCOPE_COMPANY_ID),
            _detail("od-101-1", "合成工段", "od-101"),
            _detail("od-101-1-1", "班组", "od-101-1"),
        ],
    )
    store = FakeStore()

    stats = await sync_org_departments(store, fetcher)

    assert stats.total == 2
    assert "od-101-1-1" not in store.records
    assert fetcher.detail_requests == [["od-101", "od-101-1"]]


@pytest.mark.asyncio
async def test_sync_records_last_sync_metadata_with_counts() -> None:
    fetcher = FakeFetcher(
        departments=[_contact("od-101", "101车间", IN_SCOPE_COMPANY_ID)],
        details=[_detail("od-101", "101车间", IN_SCOPE_COMPANY_ID)],
    )
    store = FakeStore()
    started = datetime(2026, 11, 12, 0, 0, tzinfo=UTC)

    await sync_org_departments(store, fetcher, started_at=started)

    assert len(store.runs) == 1
    run = store.runs[0]
    assert run.status == "success"
    assert run.department_count == 1
    assert run.people_count == 0
    assert run.started_at == started
    assert run.finished_at is not None
    assert run.error_message is None


@pytest.mark.asyncio
async def test_sync_records_failed_run_and_keeps_existing_data() -> None:
    existing = OrgDepartmentRecord(id="od-101", name="101车间", parent_id=IN_SCOPE_COMPANY_ID)
    store = FakeStore(existing=[existing])

    class BrokenFetcher(FakeFetcher):
        async def fetch_departments(self) -> list[dict[str, Any]]:
            raise RuntimeError("feishu unavailable")

    with pytest.raises(RuntimeError):
        await sync_org_departments(
            store,
            BrokenFetcher(departments=[], details=[]),
        )

    assert store.records["od-101"].name == "101车间"
    assert store.hidden == []
    assert store.runs[-1].status == "failed"
    assert "feishu unavailable" in (store.runs[-1].error_message or "")


@pytest.mark.asyncio
async def test_sync_rolls_back_partial_writes_before_recording_failure() -> None:
    existing = OrgDepartmentRecord(id="od-existing", name="既有部门", parent_id=IN_SCOPE_COMPANY_ID)
    fetcher = FakeFetcher(
        departments=[
            _contact("od-101", "101车间", IN_SCOPE_COMPANY_ID),
            _contact("od-102", "102车间", IN_SCOPE_COMPANY_ID),
        ],
        details=[
            _detail("od-101", "101车间", IN_SCOPE_COMPANY_ID),
            _detail("od-102", "102车间", IN_SCOPE_COMPANY_ID),
        ],
    )

    class FailingStore(FakeStore):
        def __init__(self) -> None:
            super().__init__(existing=[existing])
            self.calls = 0

        async def upsert_department(self, record: OrgDepartmentRecord) -> bool:
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("database write failed")
            return await super().upsert_department(record)

    store = FailingStore()

    with pytest.raises(RuntimeError, match="database write failed"):
        await sync_org_departments(store, fetcher)

    assert set(store.records) == {"od-existing"}
    assert store.records["od-existing"].name == "既有部门"
    assert store.hidden == []
    assert store.runs[-1].status == "failed"
    assert "database write failed" in (store.runs[-1].error_message or "")
