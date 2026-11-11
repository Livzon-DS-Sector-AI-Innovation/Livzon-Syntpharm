"""偏差台账的三个定时扫描任务。

| 任务 | 触发时间 | 行为 |
|---|---|---|
| 超期提醒 | 每天 09:00 | 扫描 ``pending_*`` 状态超过环节阈值的偏差，提醒当前处理人 |
| 周确认提醒 | 每周五 10:00 | 未提交本周生产/偏差状态确认的部门，提醒部门负责人与 GMP 人员 |
| 生产车间未提交 | 每周一 09:00 | 上一周没有任何偏差提交的生产车间，向配置的群聊汇总通报 |

三个任务都通过 ``SchedulerEngine`` 注册，开关读取 ``core.module_settings``
（module=``quality-deviation``，key=``NOTIFY``）。扫描按批限量，避免一次性打爆飞书接口。
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.scheduler import ScheduleConfig, ScheduleStrategy, TaskDefinition
from app.platform.scheduler.registry import scheduler_registry

from . import deviation_ledger_constants as constants
from . import deviation_notify as notify
from .deviation_config_service import current_week_key
from .deviation_department_models import DepartmentContact, DepartmentWeeklyConfirmation
from .deviation_flow import (
    STATUS_TO_STEP,
    HandlerDirectory,
    resolve_step_handlers,
)
from .deviation_ledger_constants import LedgerStatus
from .deviation_ledger_models import DeviationLedger

logger = logging.getLogger(__name__)

OVERDUE_JOB_ID = "deviation_overdue_daily"
WEEKLY_CONFIRM_JOB_ID = "deviation_weekly_confirm"
WORKSHOP_CHECK_JOB_ID = "deviation_workshop_submit_check"

#: 单次扫描最多处理的偏差数，避免定时任务一次性发送过多消息
_MAX_ITEMS_PER_RUN = 100
#: 超期提醒不重复打扰的间隔（同一偏差每天最多一次，由任务节奏保证）
_PENDING_STATUSES: tuple[str, ...] = tuple(constants.STEP_OVERDUE_DAYS)


async def _run_with_session(handler: Callable[[AsyncSession], Awaitable[dict[str, Any]]], task_name: str) -> None:
    """统一取会话 + 异常兜底（定时任务不允许抛未捕获异常）。"""
    from app.platform.database import get_db_session

    try:
        async for session in get_db_session():
            result = await handler(session)
            logger.info(
                "deviation scheduled task done: %s",
                task_name,
                extra={"app_module": "quality", "result": result},
            )
            break
    except Exception:  # noqa: BLE001 - 定时任务必须自兜底
        logger.exception("deviation scheduled task failed: %s", task_name, extra={"app_module": "quality"})


async def _contacts(db: AsyncSession) -> dict[str, DepartmentContact]:
    rows = await db.execute(select(DepartmentContact).where(DepartmentContact.is_deleted.is_(False)))  # noqa: E712
    return {row.department: row for row in rows.scalars().all() if row.department}


def _days_between(start: datetime | None, now: datetime) -> int:
    if start is None:
        return 0
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return max(int((now - start).total_seconds() // 86400), 0)


# ── 1. 超期提醒 ───────────────────────────────────────────────────────


async def run_overdue_reminder() -> None:
    """扫描超期偏差并提醒当前处理人。"""

    async def _handler(db: AsyncSession) -> dict[str, Any]:
        config = await notify.load_notify_settings()
        if not config.enabled_for("overdue"):
            return {"skipped": "disabled"}
        now = datetime.now(UTC)
        conditions = [
            and_(
                DeviationLedger.status == status,
                DeviationLedger.status_updated_at < now - timedelta(days=days),
            )
            for status, days in constants.STEP_OVERDUE_DAYS.items()
        ]
        rows = (
            (
                await db.execute(
                    select(DeviationLedger)
                    .where(
                        DeviationLedger.is_deleted.is_(False),  # noqa: E712
                        or_(*conditions),
                    )
                    .order_by(DeviationLedger.status_updated_at.asc())
                    .limit(_MAX_ITEMS_PER_RUN)
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            return {"notified": 0}

        contacts = await _contacts(db)
        notified = 0
        for row in rows:
            step = STATUS_TO_STEP.get(row.status)
            if step is None:
                continue
            directory = await HandlerDirectory.load(db, row, contacts)
            handlers = resolve_step_handlers(row, contacts, directory)
            recipients = directory.refs(handlers.get(step, []))
            reporter = directory.ref(row.reporter_id)
            if not recipients and reporter is not None:
                recipients = [reporter]
            if not recipients:
                continue
            days = _days_between(row.status_updated_at, now)
            notice = notify.to_notice(row, reporter_name=reporter.name if reporter else "")
            body = (
                f"**{notice.code}** {notice.title}\n"
                f"部门：{notice.department}\n"
                f"当前环节：{constants.status_label(row.status)}\n"
                f"已停留：{days} 天\n"
                f"请及时处理。"
            )
            await notify.send_to_users(
                recipients,
                title="偏差处理超期提醒",
                content=body,
                url=notify.detail_url(notice.id),
                action_text="去处理",
            )
            notified += 1
        return {"scanned": len(rows), "notified": notified}

    await _run_with_session(_handler, OVERDUE_JOB_ID)


# ── 2. 周确认提醒 ─────────────────────────────────────────────────────


async def run_weekly_confirm_reminder() -> None:
    """提醒尚未提交本周确认的部门。"""

    async def _handler(db: AsyncSession) -> dict[str, Any]:
        config = await notify.load_notify_settings()
        if not config.enabled_for("weekly"):
            return {"skipped": "disabled"}
        week = current_week_key()
        contacts = await _contacts(db)
        if not contacts:
            return {"skipped": "no_contacts"}

        confirmed = set(
            (
                await db.execute(
                    select(DepartmentWeeklyConfirmation.department).where(
                        DepartmentWeeklyConfirmation.week_key == week,
                        DepartmentWeeklyConfirmation.is_deleted.is_(False),  # noqa: E712
                    )
                )
            ).scalars()
        )

        pending = [contact for name, contact in contacts.items() if name not in confirmed]
        if not pending:
            return {"week": week, "pending": 0}

        directory = await HandlerDirectory.load_for_ids(db, contacts)
        notified = 0
        for contact in pending:
            tokens: list[str | uuid.UUID] = list(contact.gmp_staff_ids or [])
            if contact.dept_head_id is not None:
                tokens.append(contact.dept_head_id)
            if contact.production_head_id is not None:
                tokens.append(contact.production_head_id)
            recipients = directory.refs(directory.resolve(tokens))
            if not recipients:
                continue
            body = (
                f"部门：{contact.department}\n"
                f"周次：{week}\n"
                f"请确认本周生产状态（生产 / 停产）与偏差提交状态（已提交 / 未提交）。"
            )
            await notify.send_to_users(
                recipients,
                title="本周生产与偏差状态待确认",
                content=body,
                url=notify.absolute_url("/quality/deviation"),
                action_text="立即确认",
            )
            notified += 1
        return {"week": week, "pending": len(pending), "notified": notified}

    await _run_with_session(_handler, WEEKLY_CONFIRM_JOB_ID)


# ── 3. 生产车间未提交偏差群通知 ───────────────────────────────────────


async def run_workshop_submit_check() -> None:
    """上一周没有任何偏差记录的生产车间，向群聊汇总通报。"""

    async def _handler(db: AsyncSession) -> dict[str, Any]:
        config = await notify.load_notify_settings()
        if not config.enabled_for("gmp_group") or not config.chat_id:
            return {"skipped": "disabled_or_no_chat"}
        since = datetime.now(UTC) - timedelta(days=7)
        contacts = await _contacts(db)
        workshops = [contact for contact in contacts.values() if contact.is_production_workshop]
        if not workshops:
            return {"skipped": "no_workshop"}

        submitted = set(
            (
                await db.execute(
                    select(DeviationLedger.department).where(
                        DeviationLedger.is_deleted.is_(False),  # noqa: E712
                        DeviationLedger.department.in_([contact.department for contact in workshops]),
                        DeviationLedger.created_at >= since,
                        DeviationLedger.status != LedgerStatus.CANCELLED.value,
                    )
                )
            ).scalars()
        )
        missing = [contact.department for contact in workshops if contact.department not in submitted]
        if not missing:
            return {"workshops": len(workshops), "missing": 0}

        body = "以下生产车间最近 7 天未提交任何偏差：\n" + "\n".join(f"- {department}" for department in missing)
        await notify.broadcast_to_group("生产车间偏差提交情况通报", body)
        return {"workshops": len(workshops), "missing": len(missing)}

    await _run_with_session(_handler, WORKSHOP_CHECK_JOB_ID)


# ── 任务定义与注册 ───────────────────────────────────────────────────

overdue_reminder_task = TaskDefinition(
    name="偏差处理超期提醒",
    # 每工作日 09:00（与妙搭触发器一致）
    schedule=ScheduleConfig(strategy=ScheduleStrategy.CRON, expression="0 9 * * 1-5", timezone="Asia/Shanghai"),
    coro=run_overdue_reminder,
    module="quality",
    settings_toggle_key="",
)

weekly_confirm_task = TaskDefinition(
    name="偏差周确认提醒",
    # 每周五 16:00（与妙搭触发器一致）
    schedule=ScheduleConfig(strategy=ScheduleStrategy.CRON, expression="0 16 * * 5", timezone="Asia/Shanghai"),
    coro=run_weekly_confirm_reminder,
    module="quality",
    settings_toggle_key="",
)

workshop_submit_task = TaskDefinition(
    name="生产车间未提交偏差通报",
    # 每周五 09:00（与妙搭触发器一致）
    schedule=ScheduleConfig(strategy=ScheduleStrategy.CRON, expression="0 9 * * 5", timezone="Asia/Shanghai"),
    coro=run_workshop_submit_check,
    module="quality",
    settings_toggle_key="",
)


def register() -> None:
    """注册三个定时任务（main.py 以 try/except 包裹，失败不影响启动）。"""
    scheduler_registry.register_task(overdue_reminder_task)
    scheduler_registry.register_task(weekly_confirm_task)
    scheduler_registry.register_task(workshop_submit_task)
    logger.info("偏差台账定时任务已注册：超期提醒 / 周确认提醒 / 生产车间未提交通报")
