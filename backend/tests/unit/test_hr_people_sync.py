"""Personnel mirror sync seam (ticket #198).

Seam: ``sync_employee_profiles(store, fetcher)`` with an in-memory store and a
fake directory fetcher. Catches:
- batching of known open ids into requests of at most 100;
- omitted Feishu keys stored as empty values;
- resigned fields captured from the directory payload;
- no deletion or disabling of known people that this run did not return;
- department ids falling back to the platform directory membership.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.modules.hr.people_domain import EmployeeProfileRecord
from app.modules.hr.people_sync import (
    KnownPerson,
    PeopleSyncStats,
    sync_employee_profiles,
)


class FakeFetcher:
    def __init__(self, payload_by_open_id: dict[str, dict[str, Any]]) -> None:
        self.payload_by_open_id = payload_by_open_id
        self.batches: list[list[str]] = []

    async def fetch_employees(self, open_ids: list[str]) -> list[dict[str, Any]]:
        self.batches.append(list(open_ids))
        return [self.payload_by_open_id[open_id] for open_id in open_ids if open_id in self.payload_by_open_id]


class FakeStore:
    def __init__(
        self,
        known: list[KnownPerson],
        existing: list[EmployeeProfileRecord] | None = None,
    ) -> None:
        self.known = known
        self.profiles: dict[str, EmployeeProfileRecord] = {p.open_id: p for p in existing or []}
        self.department_ids_by_open_id: dict[str, list[str]] = {}
        self.deleted: list[str] = []

    async def list_known_people(self) -> list[KnownPerson]:
        return list(self.known)

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

    async def delete_profile(self, open_id: str) -> None:
        self.deleted.append(open_id)


def _known(*open_ids: str) -> list[KnownPerson]:
    return [KnownPerson(open_id=open_id, department_ids=["od-101"]) for open_id in open_ids]


async def test_sync_fetches_known_people_in_batches_of_at_most_100() -> None:
    open_ids = [f"ou-{index:03d}" for index in range(205)]
    fetcher = FakeFetcher({open_id: {"open_id": open_id, "name": open_id} for open_id in open_ids})
    store = FakeStore(known=_known(*open_ids))

    stats = await sync_employee_profiles(store, fetcher)

    assert [len(batch) for batch in fetcher.batches] == [100, 100, 5]
    assert stats == PeopleSyncStats(total=205, created=205, updated=0, batches=3)
    assert set(store.profiles) == set(open_ids)


async def test_sync_stores_omitted_fields_as_empty_values() -> None:
    fetcher = FakeFetcher({"ou-empty": {"open_id": "ou-empty", "name": "李四"}})
    store = FakeStore(known=_known("ou-empty"))

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
    assert record.department_ids == []


async def test_sync_captures_resigned_fields() -> None:
    fetcher = FakeFetcher(
        {
            "ou-left": {
                "open_id": "ou-left",
                "name": "王五",
                "is_resigned": True,
                "resign_time": "2026-10-01 12:00:00",
                "resign_date": "2026-10-01",
                "resign_type": "主动离职",
                "resign_reason": "个人原因",
                "resign_remark": "已交接",
            }
        }
    )
    store = FakeStore(known=_known("ou-left"))

    await sync_employee_profiles(store, fetcher)

    record = store.profiles["ou-left"]
    assert record.is_resigned is True
    assert record.resign_time == "2026-10-01 12:00:00"
    assert record.resign_date == date(2026, 10, 1)
    assert record.resign_type == "主动离职"
    assert record.resign_reason == "个人原因"
    assert record.resign_remark == "已交接"


async def test_sync_never_deletes_people_missing_from_the_response() -> None:
    existing = EmployeeProfileRecord(open_id="ou-gone", name="已离开")
    fetcher = FakeFetcher({"ou-1": {"open_id": "ou-1", "name": "张三"}})
    store = FakeStore(known=_known("ou-1", "ou-gone"), existing=[existing])

    stats = await sync_employee_profiles(store, fetcher)

    assert stats.total == 1
    assert "ou-gone" in store.profiles
    assert store.profiles["ou-gone"].name == "已离开"
    assert store.deleted == []


async def test_sync_falls_back_to_platform_department_membership() -> None:
    fetcher = FakeFetcher(
        {
            "ou-1": {"open_id": "ou-1", "name": "张三"},
            "ou-2": {
                "open_id": "ou-2",
                "name": "李四",
                "employee_order_in_departments": [{"department_id": "od-202"}],
            },
        }
    )
    store = FakeStore(
        known=[
            KnownPerson(open_id="ou-1", department_ids=["od-101"]),
            KnownPerson(open_id="ou-2", department_ids=["od-101"]),
        ]
    )
    synced_at = datetime(2026, 11, 12, 0, 0, tzinfo=UTC)

    await sync_employee_profiles(store, fetcher, synced_at=synced_at)

    assert store.department_ids_by_open_id["ou-1"] == ["od-101"]
    assert store.department_ids_by_open_id["ou-2"] == ["od-202"]
    assert store.profiles["ou-1"].last_synced_at == synced_at
