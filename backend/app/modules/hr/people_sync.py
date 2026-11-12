"""Personnel mirror sync for the Feishu-backed 员工档案 (ticket #198).

The sync is written against two narrow ports:

* :class:`EmployeeProfileFetcher` — the Feishu directory side;
* :class:`EmployeeProfileStore` — the mirror/platform-directory side.

Production wires the real Feishu HTTP fetcher and the SQLAlchemy store; unit
tests wire fakes. Known open ids come from the platform directory (scoped to
the in-scope company by the store). The sync enriches only those ids and never
deletes or disables anyone: people the directory no longer returns keep their
previous mirror row.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from app.modules.hr.people_domain import EmployeeProfileRecord, parse_directory_employee

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 100


class EmployeeProfileFetcher(Protocol):
    """Feishu side of the personnel sync."""

    async def fetch_employees(self, open_ids: list[str]) -> list[dict[str, Any]]:
        """Return ``directory/v1/employees/mget`` payloads for one batch."""


@dataclass(frozen=True)
class KnownPerson:
    """A platform-directory person that the mirror should enrich."""

    open_id: str
    department_ids: list[str] = field(default_factory=list)


class EmployeeProfileStore(Protocol):
    """Mirror side of the personnel sync."""

    async def list_known_people(self) -> list[KnownPerson]:
        """Return in-scope people from the platform directory plus existing rows."""

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


def _unique_known(people: list[KnownPerson]) -> list[KnownPerson]:
    seen: set[str] = set()
    result: list[KnownPerson] = []
    for person in people:
        if not person.open_id or person.open_id in seen:
            continue
        seen.add(person.open_id)
        result.append(person)
    return result


async def sync_employee_profiles(
    store: EmployeeProfileStore,
    fetcher: EmployeeProfileFetcher,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    synced_at: datetime | None = None,
) -> PeopleSyncStats:
    """Enrich every known person from the Feishu directory in bounded batches.

    Empty/omitted Feishu fields are written as empty values. Failures propagate
    so the owning org sync can record a failed run while keeping previous data.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    known = _unique_known(await store.list_known_people())
    known_by_open_id = {person.open_id: person for person in known}
    synced = synced_at or datetime.now(UTC)

    created = 0
    total = 0
    batches = 0
    for start in range(0, len(known), batch_size):
        batch = known[start : start + batch_size]
        batches += 1
        payloads = await fetcher.fetch_employees([person.open_id for person in batch])
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            record = parse_directory_employee(payload)
            if record is None:
                continue
            known_person = known_by_open_id.get(record.open_id)
            if known_person is None:
                continue
            department_ids = record.department_ids or known_person.department_ids
            record.last_synced_at = synced
            if await store.upsert_profile(record, department_ids=list(department_ids)):
                created += 1
            total += 1

    logger.info(
        "hr employee profile sync finished",
        extra={
            "biz_module": "hr",
            "people_count": total,
            "created": created,
            "batches": batches,
        },
    )
    return PeopleSyncStats(total=total, created=created, updated=total - created, batches=batches)
