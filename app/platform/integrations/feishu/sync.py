"""Generic Feishu-to-local-DB sync orchestration.

Provides a single `run_sync` helper that replaces the copy-pasted
"fetch -> parse -> upsert -> stats" pattern found in every HR and
product service method.
"""

import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

SyncStats = dict[str, int]


async def run_sync(
    *,
    fetch_records: Callable[[], Coroutine[Any, Any, list[dict]]],
    parse_record: Callable[[dict], dict | None],
    upsert_record: Callable[[dict], Coroutine[Any, Any, None]],
    get_existing: Callable[[str], Coroutine[Any, Any, Any | None]],
    get_record_id: Callable[[dict], str | None],
    post_process: Callable[[Any, dict], Coroutine[Any, Any, None]] | None = None,
) -> SyncStats:
    """Generic sync orchestrator: fetch -> parse -> upsert -> stats.

    Args:
        fetch_records: Coroutine that returns raw Feishu record dicts.
        parse_record: Callable that converts a raw record to local DB kwargs
                      (returns None to skip).
        upsert_record: Coroutine that writes/updates the local DB record.
        get_existing: Coroutine that fetches the local DB record by its key
                      (used to distinguish created vs updated).
        get_record_id: Callable that extracts the unique key from parsed data.
        post_process: Optional coroutine called after a successful upsert,
                      receiving (existing_record, parsed_data).

    Returns:
        {"created": int, "updated": int, "failed": int, "total": int}
    """
    raw_records = await fetch_records()
    stats: SyncStats = {
        "created": 0,
        "updated": 0,
        "failed": 0,
        "total": len(raw_records),
    }

    for rec in raw_records:
        try:
            parsed = parse_record(rec)
            if not parsed:
                stats["failed"] += 1
                continue

            rid = get_record_id(parsed)
            if not rid:
                stats["failed"] += 1
                continue

            await upsert_record(parsed)

            existing = await get_existing(rid)
            if existing and existing.created_at and _is_newly_created(existing):
                stats["created"] += 1
            else:
                stats["updated"] += 1

            if post_process:
                await post_process(existing, parsed)

        except Exception:
            logger.exception("Failed to sync Feishu record %s", rec.get("record_id"))
            stats["failed"] += 1

    return stats


def _is_newly_created(existing: Any) -> bool:
    """Heuristic: record created within last 60 seconds -> treat as 'created'."""
    created_at = existing.created_at
    if not created_at:
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return (datetime.now(UTC) - created_at).total_seconds() < 60
