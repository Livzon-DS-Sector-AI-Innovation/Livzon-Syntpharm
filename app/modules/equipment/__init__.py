from typing import Any

from app.modules.equipment.api import router
from app.shared.lifecycle import register_background_worker

__all__ = ["router"]


# ── Background worker registration ────────────────────────────


async def _start_equipment_ws() -> Any:
    """Start equipment module's Feishu WebSocket client."""
    from app.modules.equipment.feishu.ws_client import start_equipment_ws

    await start_equipment_ws()


async def _stop_equipment_ws() -> Any:
    """Stop equipment module's Feishu WebSocket client."""
    from app.modules.equipment.feishu.ws_client import stop_equipment_ws

    await stop_equipment_ws()


register_background_worker(
    name="equipment.ws_client",
    start=_start_equipment_ws,
    stop=_stop_equipment_ws,
)


async def _start_equipment_scheduler() -> Any:
    """Start equipment module's maintenance plan and timeout scan loops."""
    import asyncio

    from app.modules.equipment.scheduler import (
        maintenance_plan_loop,
        timeout_scan_loop,
    )

    # Run both loops concurrently
    await asyncio.gather(
        maintenance_plan_loop(),
        timeout_scan_loop(),
    )


async def _stop_equipment_scheduler() -> Any:
    """Stop equipment module's scheduler loops."""
    from app.modules.equipment.scheduler import (
        stop_maintenance_plan_flag,
        stop_timeout_flag,
    )

    stop_maintenance_plan_flag.set()
    stop_timeout_flag.set()


register_background_worker(
    name="equipment.scheduler",
    start=_start_equipment_scheduler,
    stop=_stop_equipment_scheduler,
)
