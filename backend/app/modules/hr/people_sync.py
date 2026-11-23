"""Personnel mirror sync for the Feishu-backed 员工档案 (ticket #198 / #219).

The sync is written against two narrow ports:

* :class:`EmployeeProfileFetcher` — the Feishu directory filter side;
* :class:`EmployeeProfileStore` — the HR mirror side.

Production wires the real Feishu HTTP fetcher and the SQLAlchemy store; unit
tests wire fakes. In-scope department ids come from ``hr.departments`` and are
passed to the Feishu employee filter in one paginated query.

Ticket #219 turns the sync into a faithful mirror: inside a successful,
non-empty run, people who fall out of the directory stop being current
(``is_current=False``) instead of being physically deleted, so historical
ledgers keep their ``hr.employee_profiles.id`` reference. Three guardrails keep
a transient Feishu failure from emptying every picker:

1. a failed fetch or a zero-record fetch aborts the run and touches nothing;
2. a run that would mark more than :data:`REMOVAL_RATIO_THRESHOLD` of the
   current mirror as not current (or would leave fewer than
   :data:`MIN_RETAINED_PROFILES`) refuses removals and only upserts;
3. removals only run after every fetched person has been upserted.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from app.modules.hr.people_domain import EmployeeProfileRecord, parse_directory_employee

logger = logging.getLogger(__name__)

#: Share of the current mirror a single run may retire before the guardrail trips.
REMOVAL_RATIO_THRESHOLD = 0.2
#: Removals never leave the mirror below this many current rows.
MIN_RETAINED_PROFILES = 1


class ProfilesFetchEmptyError(RuntimeError):
    """Raised when the directory returns zero people for a non-empty scope.

    The caller (HR org sync) records a failed run and rolls the session back, so
    the previous mirror stays untouched.
    """


class EmployeeProfileFetcher(Protocol):
    """Feishu side of the personnel sync."""

    async def fetch_employees_by_filter(self, department_ids: list[str]) -> list[dict[str, Any]]:
        """Return employees for the in-scope departments."""


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
        """Insert or update the current row by open id; return True when created."""

    async def list_current_open_ids(self) -> set[str]:
        """Return the open ids of every row currently marked as current."""

    async def mark_removed(self, open_ids: list[str], *, removed_at: datetime) -> int:
        """Flag rows as no longer current; return how many rows changed."""


@dataclass(frozen=True)
class PeopleSyncStats:
    total: int
    created: int
    updated: int
    batches: int
    removed: int = 0
    removal_skipped: bool = False


async def sync_employee_profiles(
    store: EmployeeProfileStore,
    fetcher: EmployeeProfileFetcher,
    *,
    synced_at: datetime | None = None,
    removal_ratio_threshold: float = REMOVAL_RATIO_THRESHOLD,
    min_retained_profiles: int = MIN_RETAINED_PROFILES,
) -> PeopleSyncStats:
    """Fetch everyone in the in-scope departments and refresh the mirror.

    Empty/omitted Feishu fields are written as empty values. Fetch failures
    propagate so the owning org sync records a failed run while keeping previous
    data. A zero-record result for a non-empty scope raises
    :class:`ProfilesFetchEmptyError` for the same reason.
    """
    department_ids = await store.list_scope_department_ids()
    if not department_ids:
        logger.warning(
            "hr employee profile sync skipped: no scoped departments",
            extra={"biz_module": "hr"},
        )
        return PeopleSyncStats(total=0, created=0, updated=0, batches=0)

    payloads = await fetcher.fetch_employees_by_filter(department_ids)
    if not payloads:
        raise ProfilesFetchEmptyError(
            f"employee filter returned no records for {len(department_ids)} departments; mirror left untouched"
        )
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

    removed, removal_skipped = await _retire_missing(
        store,
        seen=seen,
        removed_at=synced,
        removal_ratio_threshold=removal_ratio_threshold,
        min_retained_profiles=min_retained_profiles,
    )

    logger.info(
        "hr employee profile sync finished",
        extra={
            "biz_module": "hr",
            "people_count": total,
            "created_count": created,
            "removed_count": removed,
            "removal_skipped": removal_skipped,
            "batches": 1,
        },
    )
    return PeopleSyncStats(
        total=total,
        created=created,
        updated=total - created,
        batches=1,
        removed=removed,
        removal_skipped=removal_skipped,
    )


async def _retire_missing(
    store: EmployeeProfileStore,
    *,
    seen: set[str],
    removed_at: datetime,
    removal_ratio_threshold: float,
    min_retained_profiles: int,
) -> tuple[int, bool]:
    """Mark current rows missing from this run as not current.

    Returns ``(removed_count, skipped_by_guardrail)``. A guardrail trip leaves
    every row untouched and logs the numbers used for the decision.
    """
    current = await store.list_current_open_ids()
    missing = sorted(current - seen)
    if not missing:
        return 0, False

    remaining = len(current) - len(missing)
    ratio = len(missing) / len(current) if current else 0.0
    if ratio > removal_ratio_threshold or remaining < min_retained_profiles:
        logger.warning(
            "hr employee profile sync: removal skipped by guardrail",
            extra={
                "biz_module": "hr",
                "current_count": len(current),
                "missing_count": len(missing),
                "removed_ratio": round(ratio, 4),
                "ratio_threshold": removal_ratio_threshold,
                "remaining_count": remaining,
                "min_retained": min_retained_profiles,
            },
        )
        return 0, True

    return await store.mark_removed(missing, removed_at=removed_at), False
