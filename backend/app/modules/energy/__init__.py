from typing import Any

from app.modules.energy.api import router
from app.modules.energy.scheduler import (
    bitable_daily_sync_loop,
    bitable_monthly_sync_loop,
    energy_collection_loop,
    stop_bitable_daily_sync_flag,
    stop_bitable_sync_flag,
    stop_energy_collection_flag,
)
from app.shared.lifecycle import register_background_worker

__all__ = [
    "router",
    "energy_collection_loop",
    "bitable_monthly_sync_loop",
    "bitable_daily_sync_loop",
    "stop_energy_collection_flag",
    "stop_bitable_sync_flag",
    "stop_bitable_daily_sync_flag",
]


# ── Background worker registration ────────────────────────────


async def _start_energy_collection() -> Any:
    await energy_collection_loop()


async def _stop_energy_collection() -> Any:
    stop_energy_collection_flag.set()


register_background_worker(
    name="energy.collection",
    start=_start_energy_collection,
    stop=_stop_energy_collection,
)


async def _start_bitable_monthly_sync() -> Any:
    await bitable_monthly_sync_loop()


async def _stop_bitable_monthly_sync() -> Any:
    stop_bitable_sync_flag.set()


register_background_worker(
    name="energy.bitable_monthly_sync",
    start=_start_bitable_monthly_sync,
    stop=_stop_bitable_monthly_sync,
)


async def _start_bitable_daily_sync() -> Any:
    await bitable_daily_sync_loop()


async def _stop_bitable_daily_sync() -> Any:
    stop_bitable_daily_sync_flag.set()


register_background_worker(
    name="energy.bitable_daily_sync",
    start=_start_bitable_daily_sync,
    stop=_stop_bitable_daily_sync,
)
