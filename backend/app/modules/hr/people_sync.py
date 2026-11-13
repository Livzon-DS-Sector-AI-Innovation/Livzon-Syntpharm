"""Personnel mirror sync for the Feishu-backed 员工档案 (ticket #198).

The sync is written against two narrow ports:

* :class:`EmployeeProfileFetcher` — the Feishu directory filter side;
* :class:`EmployeeProfileStore` — the HR mirror side.

Production wires the real Feishu HTTP fetcher and the SQLAlchemy store; unit
tests wire fakes. In-scope department ids come from ``hr.departments`` and are
passed to the Feishu employee filter in one paginated query. The sync never
deletes or disables anyone: people the directory no longer returns keep their
previous mirror row.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from app.modules.hr.people_domain import EmployeeProfileRecord, parse_directory_employee

logger = logging.getLogger(__name__)


class EmployeeProfileFetcher(Protocol):
    """Feishu side of the personnel sync."""

    async def fetch_employees_by_filter(self, department_ids: list[str]) -> list[dict[str, Any]]:
        """Return employees for the in-scope departments (all statuses)."""


class EmployeeProfileStore(Protocol):
    """Mirror side of the personnel sync."""

    async def list_scope_department_ids(self) -> list[str]:
        """Return non-hidden level 1/2 Feishu department ids from HR storage."""

    async def upsert_profile(
        self,
        record: EmployeeProfileRecord,
        *,
        department_ids: list[str],
    ) -> bool:
        """Insert or update by open id; return True when created."""


@dataclass(frozen=True)
class PeopleSyncStats:
    total: int
    created: int
    updated: int
    batches: int


async def sync_employee_profiles(
    store: EmployeeProfileStore,
    fetcher: EmployeeProfileFetcher,
    *,
    synced_at: datetime | None = None,
) -> PeopleSyncStats:
    """Fetch everyone in the in-scope departments and upsert the mirror.

    Empty/omitted Feishu fields are written as empty values. Failures propagate
    so the owning org sync can record a failed run while keeping previous data.
    """
    department_ids = await store.list_scope_department_ids()
    if not department_ids:
        return PeopleSyncStats(total=0, created=0, updated=0, batches=0)

    payloads = await fetcher.fetch_employees_by_filter(department_ids)
    synced = synced_at or datetime.now(UTC)

    created = 0
    seen: set[str] = set()
    total = 0
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        record = parse_directory_employee(payload)
        if record is None or record.open_id in seen:
            continue
        seen.add(record.open_id)
        record.last_synced_at = synced
        if await store.upsert_profile(record, department_ids=list(record.department_ids)):
            created += 1
        total += 1

    logger.info(
        "hr employee profile sync finished",
        extra={
            "biz_module": "hr",
            "people_count": total,
            "created_count": created,
            "batches": 1,
        },
    )
    return PeopleSyncStats(total=total, created=created, updated=total - created, batches=1)
