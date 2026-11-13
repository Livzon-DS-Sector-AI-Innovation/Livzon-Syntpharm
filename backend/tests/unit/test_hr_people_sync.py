"""Personnel mirror sync seam (ticket #198 / filter-based sync).

Seam: ``sync_employee_profiles(store, fetcher)`` with an in-memory store and a
fake employee-filter fetcher. Catches:
- in-scope department ids passed to the Feishu filter;
- duplicate people deduped by open id;
- omitted Feishu keys stored as empty values;
- resigned fields captured;
- no deletion or disabling of known people missing from the response.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.modules.hr.people_domain import EmployeeProfileRecord
from app.modules.hr.people_sync import PeopleSyncStats, sync_employee_profiles


class FakeFetcher:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.department_requests: list[list[str]] = []

    async def fetch_employees_by_filter(self, department_ids: list[str]) -> list[dict[str, Any]]:
        self.department_requests.append(list(department_ids))
        return list(self.payloads)


class FakeStore:
    def __init__(
        self,
        department_ids: list[str],
        existing: list[EmployeeProfileRecord] | None = None,
    ) -> None:
        self.department_ids = department_ids
        self.profiles: dict[str, EmployeeProfileRecord] = {p.open_id: p for p in existing or []}
        self.department_ids_by_open_id: dict[str, list[str]] = {}

    async def list_scope_department_ids(self) -> list[str]:
        return list(self.department_ids)

    async def upsert_profile(
        self,
        record: EmployeeProfileRecord,
        *,
        department_ids: list[str],
    ) -> bool:
        created = record.open_id not in self.profiles
        self.department_ids_by_open_id[record.open_id] = list(department_ids)
        self.profiles[record.open_id] = record
        return created


def _payload(open_id: str, name: str, **extra: Any) -> dict[str, Any]:
    return {
        "base_info": {
            "employee_id": open_id,
            "name": {"name": {"default_value": name}},
            "departments": [{"department_id": "od-101", "name": {"default_value": "101车间"}}],
        },
        "work_info": {},
        **extra,
    }


async def test_sync_passes_scope_departments_and_upserts_filter_results() -> None:
    payloads = [_payload("ou-1", "张三"), _payload("ou-2", "李四"), _payload("ou-1", "张三")]
    fetcher = FakeFetcher(payloads)
    store = FakeStore(department_ids=["od-101", "od-101-1"])

    stats = await sync_employee_profiles(store, fetcher)

    assert fetcher.department_requests == [["od-101", "od-101-1"]]
    assert stats == PeopleSyncStats(total=2, created=2, updated=0, batches=1)
    assert set(store.profiles) == {"ou-1", "ou-2"}


async def test_sync_stores_omitted_fields_as_empty_values() -> None:
    fetcher = FakeFetcher([_payload("ou-empty", "李四")])
    store = FakeStore(department_ids=["od-101"])

    await sync_employee_profiles(store, fetcher)

    record = store.profiles["ou-empty"]
    assert record.name == "李四"
    assert record.mobile == ""
    assert record.email == ""
    assert record.email_aliases == []
    assert record.description == ""
    assert record.employee_no == ""
    assert record.job_title_name == ""
    assert record.hire_date is None
    assert record.work_place_id == ""
    assert record.dotted_line_leader_ids == []
    assert record.positions == []


async def test_sync_captures_resigned_fields() -> None:
    payload = _payload(
        "ou-left",
        "王五",
        **{
            "base_info": {
                "employee_id": "ou-left",
                "name": {"name": {"default_value": "王五"}},
                "departments": [{"department_id": "od-101"}],
                "is_resigned": True,
                "resign_time": "2026-10-01",
            },
            "work_info": {
                "resign_date": "2026-10-01",
                "resign_type": "主动离职",
                "resign_reason": "个人原因",
                "resign_remark": "已交接",
            },
        },
    )
    fetcher = FakeFetcher([payload])
    store = FakeStore(department_ids=["od-101"])

    await sync_employee_profiles(store, fetcher)

    record = store.profiles["ou-left"]
    assert record.is_resigned is True
    assert record.resign_time == "2026-10-01"
    assert record.resign_date == date(2026, 10, 1)
    assert record.resign_type == "主动离职"
    assert record.resign_reason == "个人原因"
    assert record.resign_remark == "已交接"


async def test_sync_never_deletes_people_missing_from_the_response() -> None:
    existing = EmployeeProfileRecord(open_id="ou-gone", name="已离开")
    fetcher = FakeFetcher([_payload("ou-1", "张三")])
    store = FakeStore(department_ids=["od-101"], existing=[existing])

    stats = await sync_employee_profiles(store, fetcher)

    assert stats.total == 1
    assert "ou-gone" in store.profiles
    assert store.profiles["ou-gone"].name == "已离开"


async def test_sync_skips_fetch_without_scope_departments() -> None:
    fetcher = FakeFetcher([_payload("ou-1", "张三")])
    store = FakeStore(department_ids=[])

    stats = await sync_employee_profiles(store, fetcher)

    assert stats == PeopleSyncStats(total=0, created=0, updated=0, batches=0)
    assert fetcher.department_requests == []


async def test_sync_stamps_last_synced_at() -> None:
    fetcher = FakeFetcher([_payload("ou-1", "张三")])
    store = FakeStore(department_ids=["od-101"])
    synced_at = datetime(2026, 11, 12, 0, 0, tzinfo=UTC)

    await sync_employee_profiles(store, fetcher, synced_at=synced_at)

    assert store.profiles["ou-1"].last_synced_at == synced_at
