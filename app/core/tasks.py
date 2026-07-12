"""Fire-and-forget task utilities with proper error handling.

This module provides utilities for spawning async tasks that run in the background
without blocking the caller. All tasks are wrapped with error handling to prevent
silent failures.

TODO: Migrate to a proper task queue (e.g., Celery, ARQ) for retry, persistence,
and monitoring capabilities.
"""

import asyncio
import logging
from collections.abc import Awaitable
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def spawn_task(
    coro: Awaitable[None],
    name: str | None = None,
) -> asyncio.Task[None]:
    """Spawn a background task with proper error handling.

    Args:
        coro: The async coroutine to run
        name: Optional name for logging (defaults to a random UUID)

    Returns:
        The created asyncio.Task

    The task will log any exceptions instead of silently failing.
    """
    task_name = name or f"task-{uuid4().hex[:8]}"

    async def wrapper() -> Any:
        try:
            await coro
        except asyncio.CancelledError:
            logger.debug("Task %s cancelled", task_name)
            raise
        except Exception:
            logger.exception("Task %s failed", task_name)

    task = asyncio.create_task(wrapper(), name=task_name)
    logger.debug("Spawned background task: %s", task_name)
    return task
