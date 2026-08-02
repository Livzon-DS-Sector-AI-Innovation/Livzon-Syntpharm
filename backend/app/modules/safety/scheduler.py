"""Scheduled task engine — asyncio loop stub and manual task execution.

Scheduled tasks auto-execution loop was removed in refactor (a985172).
`scheduled_task_loop` remains as a stub to satisfy the import in app/main.py lifespan.
Manual execution via `execute_single_task` is implemented for the `run_task_now` API endpoint.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from croniter import croniter  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Stop flag, set during app shutdown
stop_scheduled_task_flag = asyncio.Event()

# Tick interval in seconds
TICK_INTERVAL = 30


async def scheduled_task_loop() -> Any:
    """Main scheduler loop stub — no-op after scheduled tasks removal.

    Launched in the FastAPI lifespan, runs until stop_scheduled_task_flag is set.
    """
    logger.info("Scheduled task loop started (tick=%ds) [stub]", TICK_INTERVAL)

    while not stop_scheduled_task_flag.is_set():
        try:
            await asyncio.wait_for(stop_scheduled_task_flag.wait(), timeout=TICK_INTERVAL)
        except TimeoutError:
            pass  # Normal tick timeout, loop continues

    logger.info("Scheduled task loop stopped")


def compute_next_run(cron_expression: str, start_time: datetime | None = None) -> datetime:
    """Compute the next run time from a cron expression.

    Returns a timezone-aware datetime in Asia/Shanghai.
    """
    tz = ZoneInfo("Asia/Shanghai")
    base = start_time or datetime.now(tz)
    if base.tzinfo is None:
        base = base.replace(tzinfo=tz)

    iter = croniter(cron_expression, base)
    next_time: datetime = iter.get_next(datetime)
    return next_time.replace(tzinfo=tz)


async def execute_single_task(task: Any, repo: Any) -> None:
    """Execute a single scheduled task manually.

    Called by ScheduledTaskService.run_task_now. Fetches configured data sources,
    renders the card template, and sends the card to the target Feishu chat.
    Creates a log entry tracking execution status, duration, and result.
    """
    from app.modules.safety.card_builder import build_card_json, fetch_data_sources, render_template
    from app.modules.safety.feishu.notification import send_group_card

    started_at = datetime.now(UTC)
    start_ms = time.monotonic() * 1000
    task.last_run_at = started_at

    enabled_keys: list[str] = []
    if task.data_sources:
        for ds in task.data_sources:
            if isinstance(ds, dict) and ds.get("enabled", ds.get("default_enabled", False)):
                key = ds.get("key")
                if key:
                    enabled_keys.append(key)
    if not enabled_keys and task.data_sources:
        enabled_keys = [ds["key"] for ds in task.data_sources if isinstance(ds, dict) and ds.get("key")]

    tz = ZoneInfo("Asia/Shanghai")
    now_str = started_at.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")

    log = await repo.create_task_log({
        "task_id": task.id,
        "started_at": started_at,
        "status": "running",
    })
    await repo.session.flush()

    try:
        variables = await fetch_data_sources(repo, enabled_keys)
        variables["runtime.timestamp"] = now_str

        template = task.card_template or ""
        rendered = render_template(template, variables)

        card_json = await build_card_json(
            title=task.name,
            rendered_markdown=rendered,
            header_color=task.header_color,
        )

        msg_id = await send_group_card(
            chat_id=task.feishu_chat_id,
            title=task.name,
            content=rendered,
            header_template=task.header_color,
        )

        completed_at = datetime.now(UTC)
        duration_ms = int(time.monotonic() * 1000 - start_ms)

        data_snapshot: dict[str, str] = {k: v for k, v in variables.items() if k != "runtime.timestamp"}

        await repo.update_task_log(log.id, {
            "status": "success",
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "data_snapshot": data_snapshot,
            "card_content": card_json,
            "feishu_msg_id": msg_id,
        })

        task.last_run_status = "success"
        task.last_error = None

        logger.info(
            "Scheduled task executed",
            extra={
                "task_id": str(task.id),
                "task_name": task.name,
                "log_id": str(log.id),
                "duration_ms": duration_ms,
                "feishu_msg_id": msg_id,
            },
        )

    except Exception as exc:
        completed_at = datetime.now(UTC)
        duration_ms = int(time.monotonic() * 1000 - start_ms)
        error_msg = str(exc)

        await repo.update_task_log(log.id, {
            "status": "failure",
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "error_message": error_msg,
        })

        task.last_run_status = "failure"
        task.last_error = error_msg

        logger.exception(
            "Scheduled task execution failed",
            extra={
                "task_id": str(task.id),
                "task_name": task.name,
                "log_id": str(log.id),
                "duration_ms": duration_ms,
            },
        )
