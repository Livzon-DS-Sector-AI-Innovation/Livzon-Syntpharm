from typing import Any

from app.modules.safety.api import router
from app.shared.lifecycle import register_background_worker

__all__ = ["router"]


# ── Background worker registration ────────────────────────────


async def _start_safety_ws() -> Any:
    """Start safety module's Feishu WebSocket client."""
    from app.modules.safety.feishu.event_client import start_ws

    await start_ws()


async def _stop_safety_ws() -> Any:
    """Stop safety module's Feishu WebSocket client."""
    from app.modules.safety.feishu.event_client import stop_ws

    await stop_ws()


register_background_worker(
    name="safety.ws_client",
    start=_start_safety_ws,
    stop=_stop_safety_ws,
)


async def _start_safety_scheduler() -> Any:
    """Start safety module's scheduled task loop."""
    from app.modules.safety.scheduler import scheduled_task_loop

    await scheduled_task_loop()


async def _stop_safety_scheduler() -> Any:
    """Stop safety module's scheduled task loop."""
    from app.modules.safety.scheduler import stop_scheduled_task_flag

    stop_scheduled_task_flag.set()


register_background_worker(
    name="safety.scheduler",
    start=_start_safety_scheduler,
    stop=_stop_safety_scheduler,
)


async def _start_safety_catch_up() -> Any:
    """Recover unprocessed Bitable records on startup."""
    from app.modules.safety.feishu.catch_up import recover_unprocessed_records

    await recover_unprocessed_records()


register_background_worker(
    name="safety.catch_up",
    start=_start_safety_catch_up,
)
