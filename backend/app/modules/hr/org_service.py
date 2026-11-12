"""Read model and sync orchestration for the 部门管理 org browser (ticket #197)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.exceptions import AppException
from app.core.redis import acquire_lock, release_lock
from app.modules.hr.org_domain import OrgDepartmentRecord, build_org_tree
from app.modules.hr.org_feishu import build_default_fetcher
from app.modules.hr.org_repository import (
    SqlAlchemyOrgDepartmentStore,
    get_latest_sync_run,
    resolve_leader_names,
)
from app.modules.hr.org_sync import sync_org_departments
from app.modules.hr.people_feishu import build_default_employee_fetcher
from app.modules.hr.people_repository import SqlAlchemyEmployeeProfileStore
from app.platform.identity.models import OrgSyncRun

logger = logging.getLogger(__name__)

SYNC_LOCK_KEY = "hr-org-departments-sync"
SYNC_LOCK_TIMEOUT_SECONDS = 900


def _all_leader_ids(records: list[OrgDepartmentRecord]) -> set[str]:
    return {leader_id for record in records for leader_id in record.leader_ids if leader_id}


async def get_org_tree(session: AsyncSession) -> list[dict[str, Any]]:
    store = SqlAlchemyOrgDepartmentStore(session)
    records = await store.list_departments()
    leader_names = await resolve_leader_names(session, _all_leader_ids(records))
    return build_org_tree(records, leader_names=leader_names)


async def get_sync_status(session: AsyncSession) -> dict[str, Any]:
    run = await get_latest_sync_run(session)
    if run is None:
        return {
            "status": "never",
            "last_synced_at": None,
            "department_count": 0,
            "people_count": 0,
            "error_message": None,
        }
    return {
        "status": run.status,
        "last_synced_at": run.finished_at or run.started_at,
        "department_count": run.department_count,
        "people_count": run.people_count,
        "error_message": run.error_message,
    }


async def _run_sync(session: AsyncSession) -> None:
    store = SqlAlchemyOrgDepartmentStore(session)
    people_store = SqlAlchemyEmployeeProfileStore(session)
    started = datetime.now(UTC)
    try:
        fetcher = await build_default_fetcher(session)
        people_fetcher = await build_default_employee_fetcher(session)
    except Exception as exc:
        # Credential/configuration failures happen before the HTTP fetcher exists;
        # record them here so the page still shows a failed last sync.
        await store.record_sync_run(
            status="failed",
            department_count=0,
            people_count=0,
            error_message=str(exc)[:2000],
            started_at=started,
            finished_at=datetime.now(UTC),
        )
        raise
    await sync_org_departments(
        store,
        fetcher,
        people_store=people_store,
        people_fetcher=people_fetcher,
        started_at=started,
    )


async def run_manual_org_sync(session: AsyncSession) -> dict[str, Any]:
    """Run the same sync as the nightly job, guarded by a concurrency lock."""
    if not await acquire_lock(SYNC_LOCK_KEY, timeout=SYNC_LOCK_TIMEOUT_SECONDS):
        raise AppException(status_code=409, message="组织架构同步正在进行中，请稍后再试")

    try:
        try:
            await _run_sync(session)
        except Exception:
            # The failed run is already flushed; persist it so the page can show it.
            await session.commit()
            raise
        await session.commit()
    except AppException:
        raise
    except Exception as exc:
        raise AppException(status_code=502, message=f"组织架构同步失败：{exc}") from exc
    finally:
        await release_lock(SYNC_LOCK_KEY)

    logger.info("hr org manual sync finished", extra={"biz_module": "hr"})
    return await get_sync_status(session)


def _already_synced_today(run: OrgSyncRun | None) -> bool:
    """Avoid a full org sync on every process restart after the daily one succeeded."""
    if run is None or run.status != "success":
        return False
    tz = ZoneInfo("Asia/Shanghai")
    started = run.started_at.astimezone(tz) if run.started_at.tzinfo else run.started_at.replace(tzinfo=tz)
    return started.date() == datetime.now(tz).date()


async def run_scheduled_org_sync() -> None:
    """Nightly 00:00 Asia/Shanghai job: departments first, then people.

    Both phases share one sync-run row; `people_count` reflects the number of
    personnel mirror rows enriched by the second phase.
    """
    async with async_session_factory() as session:
        if _already_synced_today(await get_latest_sync_run(session)):
            logger.info("hr org scheduled sync skipped: already succeeded today", extra={"biz_module": "hr"})
            return
        try:
            await _run_sync(session)
            await session.commit()
        except Exception:
            logger.exception("hr org scheduled sync failed", extra={"biz_module": "hr"})
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("hr org scheduled sync: failed run could not be persisted", extra={"biz_module": "hr"})
