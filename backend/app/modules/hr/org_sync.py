"""Department mirror sync for the Feishu-backed org browser (ticket #197).

The sync is written against two narrow seams:

* :class:`OrgDepartmentFetcher` — the Feishu side (contact tree + directory mget);
* :class:`OrgDepartmentStore` — the mirror side (list / upsert / hide / run log).

Production wires the real Feishu HTTP fetcher and the SQLAlchemy repository;
unit tests wire fakes. The mirror never hard-deletes: departments that are
missing from Feishu or outside the configured scope are flagged hidden.

Department data is fetched in full before department writes. The people phase
runs afterwards because it resolves scope from the department mirror. If any
read or write fails, the store session is rolled back before the failed run is
recorded, so a failed sync never leaves half-updated rows behind.

The generic ``platform.integrations.feishu.sync.run_sync`` helper is not used
here: this sync has a two-phase fetch (contact tree, then directory mget), a
batched people phase, and must fail atomically. ``run_sync`` is a per-record
loop with per-record error isolation, which cannot provide the all-or-nothing
rollback this mirror needs. Tests still inject fake fetchers at this same seam.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.modules.hr.org_domain import (
    DEFAULT_ORG_SCOPE,
    OrgDepartmentRecord,
    OrgScope,
    parse_directory_department,
    select_departments_to_hide,
)
from app.modules.hr.people_sync import (
    EmployeeProfileFetcher,
    EmployeeProfileStore,
    sync_employee_profiles,
)

logger = logging.getLogger(__name__)


class OrgDepartmentFetcher(Protocol):
    """Feishu side of the department sync."""

    async def fetch_departments(self) -> list[dict[str, Any]]:
        """Return the two-level contact tree as flat dicts with id/name/parent."""

    async def fetch_departments_detail(self, department_ids: list[str]) -> list[dict[str, Any]]:
        """Return ``directory/v1/departments/mget`` payloads for the ids."""


@dataclass(frozen=True)
class SyncRunRecord:
    """One persisted row of the org sync run log."""

    status: str
    department_count: int
    people_count: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class OrgDepartmentStore(Protocol):
    """Mirror side of the department sync."""

    async def list_departments(self) -> list[OrgDepartmentRecord]:
        """Return every mirror row, including hidden ones."""

    async def upsert_department(self, record: OrgDepartmentRecord) -> bool:
        """Insert or update by Feishu department id; return True when created."""

    async def hide_department(self, department_id: str) -> None:
        """Flag a department as removed/hidden; never delete it."""

    async def record_sync_run(self, run: SyncRunRecord, *, run_id: UUID | None = None) -> None:
        """Persist (or finish) one sync-run row."""

    async def rollback(self) -> None:
        """Discard writes made by this sync attempt."""


@dataclass(frozen=True)
class OrgSyncStats:
    total: int
    created: int
    updated: int
    hidden: int
    people: int = 0


def _contact_record(raw: dict[str, Any]) -> OrgDepartmentRecord:
    order = raw.get("order")
    try:
        order_int = int(order) if order not in (None, "") else 0
    except (TypeError, ValueError):
        order_int = 0
    return OrgDepartmentRecord(
        id=str(raw.get("department_id") or "").strip() or None,
        name=str(raw.get("name") or "").strip(),
        parent_id=str(raw.get("parent_department_id") or "").strip() or None,
        order=order_int,
    )


def _fallback_path(
    dept_id: str,
    contact_by_id: dict[str, OrgDepartmentRecord],
    scope: OrgScope,
) -> list[dict[str, str]]:
    chain: list[dict[str, str]] = []
    current = dept_id
    visited: set[str] = set()
    while current and not scope.is_root(current) and current not in visited:
        visited.add(current)
        record = contact_by_id.get(current)
        chain.append({"id": current, "name": record.name if record else ""})
        current = record.parent_id if record and record.parent_id else ""
    chain.reverse()
    return [scope.root_path_node, *chain]


def _select_in_scope(contacts: list[OrgDepartmentRecord], scope: OrgScope) -> list[OrgDepartmentRecord]:
    """Keep only 一级部门 (children of the scope root) and 二级部门."""
    level_one = [record for record in contacts if record.id and scope.is_direct_child(record.parent_id)]
    level_one_ids = {record.id for record in level_one}
    level_two = [record for record in contacts if record.id and record.parent_id in level_one_ids]
    return [*level_one, *level_two]


def _merge_detail(
    contact: OrgDepartmentRecord,
    detail: dict[str, Any] | None,
    contact_by_id: dict[str, OrgDepartmentRecord],
    scope: OrgScope,
) -> OrgDepartmentRecord:
    if detail is None:
        return OrgDepartmentRecord(
            id=contact.id,
            name=contact.name,
            parent_id=contact.parent_id,
            order=contact.order,
            order_weight=None,
            department_path=_fallback_path(contact.id or "", contact_by_id, scope),
        )

    raw = dict(detail)
    # Trust the contact tree for ids/parents: mget can return "0" when the id was
    # not requested explicitly, and the contact walk is the structural source.
    raw["department_id"] = contact.id
    raw["parent_department_id"] = contact.parent_id
    if not raw.get("name"):
        raw["name"] = contact.name

    record = parse_directory_department(raw)
    record.id = contact.id
    record.parent_id = contact.parent_id
    # directory order_weight is authoritative when present; contact order is the fallback.
    if record.order_weight is None:
        record.order = contact.order
    if not record.department_path:
        record.department_path = _fallback_path(contact.id or "", contact_by_id, scope)
    return record


async def sync_org_departments(
    store: OrgDepartmentStore,
    fetcher: OrgDepartmentFetcher,
    *,
    people_store: EmployeeProfileStore | None = None,
    people_fetcher: EmployeeProfileFetcher | None = None,
    started_at: datetime | None = None,
    scope: OrgScope = DEFAULT_ORG_SCOPE,
    run_id: UUID | None = None,
) -> OrgSyncStats:
    """Sync the scoped department tree, then people, into their mirrors.

    Department reads happen before department writes; the people phase follows
    so it can resolve scope from the mirror. Failures roll the mirror session
    back and record the failed run, so previous data stays intact.
    """
    started = started_at or datetime.now(UTC)
    try:
        raw_contacts = await fetcher.fetch_departments()
        contacts = [record for record in (_contact_record(raw) for raw in raw_contacts) if record.id]
        scoped = _select_in_scope(contacts, scope)
        contact_by_id = {record.id: record for record in scoped if record.id}

        ids = [record.id for record in scoped if record.id]
        details = await fetcher.fetch_departments_detail(ids) if ids else []
        detail_by_id = {
            str(detail.get("department_id")): detail
            for detail in details
            if isinstance(detail, dict) and detail.get("department_id")
        }

        existing = await store.list_departments()
        records = [
            _merge_detail(contact, detail_by_id.get(contact.id), contact_by_id, scope)
            for contact in scoped
            if contact.id
        ]

        created = 0
        for record in records:
            if await store.upsert_department(record):
                created += 1

        people_count = 0
        if people_store is not None and people_fetcher is not None:
            people_stats = await sync_employee_profiles(people_store, people_fetcher)
            people_count = people_stats.total

        to_hide = select_departments_to_hide(
            [
                {
                    "id": record.id,
                    "hidden": record.hidden,
                    "department_path": record.department_path,
                }
                for record in existing
            ],
            seen_ids=set(ids),
            scope=scope,
        )
        for department_id in to_hide:
            await store.hide_department(department_id)

        stats = OrgSyncStats(
            total=len(scoped),
            created=created,
            updated=len(scoped) - created,
            hidden=len(to_hide),
            people=people_count,
        )
        finished = datetime.now(UTC)
        await store.record_sync_run(
            SyncRunRecord(
                status="success",
                department_count=stats.total,
                people_count=people_count,
                error_message=None,
                started_at=started,
                finished_at=finished,
            ),
            run_id=run_id,
        )
        logger.info(
            "hr org department sync finished",
            extra={
                "biz_module": "hr",
                "department_count": stats.total,
                "created": stats.created,
                "updated": stats.updated,
                "hidden": stats.hidden,
                "people_count": stats.people,
            },
        )
        return stats
    except Exception as exc:
        await store.rollback()
        try:
            await store.record_sync_run(
                SyncRunRecord(
                    status="failed",
                    department_count=0,
                    people_count=0,
                    error_message=str(exc)[:2000],
                    started_at=started,
                    finished_at=datetime.now(UTC),
                ),
                run_id=run_id,
            )
        except Exception:
            logger.exception("hr org sync: failed run could not be recorded", extra={"biz_module": "hr"})
        logger.exception("hr org department sync failed", extra={"biz_module": "hr"})
        raise
