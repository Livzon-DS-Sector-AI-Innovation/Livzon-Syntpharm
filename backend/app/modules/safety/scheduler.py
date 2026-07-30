"""Scheduled task engine — asyncio loop stub.

Scheduled tasks module was removed in refactor (a985172).
This stub remains to satisfy the import in app/main.py lifespan.
"""

import asyncio
import logging
from datetime import datetime
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
