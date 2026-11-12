"""Read model and sync orchestration for the 部门管理 org browser (ticket #197)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.exceptions import AppException
from app.core.jobs import submit_job
from app.core.redis import acquire_lock, release_lock
from app.modules.hr.org_domain import OrgDepartmentRecord, build_org_tree
from app.modules.hr.org_feishu import build_default_fetcher
from app.modules.hr.org_repository import (
    SqlAlchemyOrgDepartmentStore,
    get_latest_sync_run,
    resolve_leader_names,
)
from app.modules.hr.org_settings import load_org_scope
from app.modules.hr.org_sync import SyncRunRecord, sync_org_departments
from app.modules.hr.people_feishu import build_default_employee_fetcher
from app.modules.hr.people_repository import SqlAlchemyEmployeeProfileStore
from app.platform.identity.models import OrgSyncRun

logger = logging.getLogger(__name__)

SYNC_LOCK_KEY = "hr-org-departments-sync"
SYNC_LOCK_TIMEOUT_SECONDS = 900
SYNC_JOB_NAME = "hr.org-sync"


def _all_leader_ids(records: list[OrgDepartmentRecord]) -> set[str]:
    return {leader_id for record in records for leader_id in record.leader_ids if leader_id}


async def get_org_tree(session: AsyncSession) -> list[dict[str, Any]]:
    scope = await load_org_scope(session)
    store = SqlAlchemyOrgDepartmentStore(session)
    records = await store.list_departments()
    leader_names = await resolve_leader_names(session, _all_leader_ids(records))
    return build_org_tree(records, leader_names=leader_names, scope=scope)


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


async def _sync_with_session(
    session: AsyncSession,
    *,
    run_id: UUID | None = None,
) -> None:
    store = SqlAlchemyOrgDepartmentStore(session)
    people_store = SqlAlchemyEmployeeProfileStore(session)
    started = datetime.now(UTC)
    try:
        scope = await load_org_scope(session)
        fetcher = await build_default_fetcher(session)
        people_fetcher = await build_default_employee_fetcher(session)
    except Exception as exc:
        # Credential/configuration failures happen before the HTTP fetcher exists;
        # record them here so the page still shows a failed last sync.
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
        raise
    await sync_org_departments(
        store,
        fetcher,
        people_store=people_store,
        people_fetcher=people_fetcher,
        started_at=started,
        scope=scope,
        run_id=run_id,
    )


async def _mark_run_failed(run_id: UUID, message: str) -> None:
    async with async_session_factory() as session:
        run = await session.get(OrgSyncRun, run_id)
        started = run.started_at if run is not None else datetime.now(UTC)
        await SqlAlchemyOrgDepartmentStore(session).record_sync_run(
            SyncRunRecord(
                status="failed",
                department_count=0,
                people_count=0,
                error_message=message[:2000],
                started_at=started,
                finished_at=datetime.now(UTC),
            ),
            run_id=run_id,
        )
        await session.commit()


async def _execute_org_sync_job(run_id: UUID) -> None:
    """Run the sync in the background; a failure leaves the previous data intact."""
    if not await acquire_lock(SYNC_LOCK_KEY, timeout=SYNC_LOCK_TIMEOUT_SECONDS):
        await _mark_run_failed(run_id, "组织架构同步正在进行中，请稍后再试")
        return

    try:
        async with async_session_factory() as session:
            try:
                await _sync_with_session(session, run_id=run_id)
            except Exception:
                # `_sync_with_session` rolled the data writes back before recording
                # the failed run, so committing here persists only the run status.
                await session.commit()
                raise
            await session.commit()
    except Exception:
        logger.exception("hr org background sync failed", extra={"biz_module": "hr"})
        raise
    finally:
        await release_lock(SYNC_LOCK_KEY)

    logger.info("hr org background sync finished", extra={"biz_module": "hr"})


async def enqueue_manual_org_sync(session: AsyncSession) -> dict[str, Any]:
    """Create a ``running`` run row and hand the work to the jobs infrastructure."""
    latest = await get_latest_sync_run(session)
    if latest is not None and latest.status == "running":
        started = latest.started_at if latest.started_at.tzinfo else latest.started_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - started < timedelta(seconds=SYNC_LOCK_TIMEOUT_SECONDS):
            raise AppException(status_code=409, message="组织架构同步正在进行中，请稍后再试")

    run = OrgSyncRun(
        status="running",
        department_count=0,
        people_count=0,
        error_message=None,
        started_at=datetime.now(UTC),
        finished_at=None,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    try:
        await submit_job(SYNC_JOB_NAME, lambda _job_id: _execute_org_sync_job(run.id))
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)[:2000]
        run.finished_at = datetime.now(UTC)
        await session.commit()
        raise AppException(status_code=502, message=f"组织架构同步任务提交失败：{exc}") from exc

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
        run = OrgSyncRun(
            status="running",
            department_count=0,
            people_count=0,
            error_message=None,
            started_at=datetime.now(UTC),
            finished_at=None,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    try:
        await _execute_org_sync_job(run_id)
    except Exception:
        logger.exception("hr org scheduled sync failed", extra={"biz_module": "hr"})
