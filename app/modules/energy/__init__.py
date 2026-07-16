from typing import Any

from app.modules.energy.api import router
from app.shared.lifecycle import register_background_worker

__all__ = ["router"]


# ── Background worker registration ────────────────────────────


async def _start_energy_collection() -> Any:
    """Start energy module's data collection loop."""
    from app.modules.energy.scheduler import energy_collection_loop

    await energy_collection_loop()


async def _stop_energy_collection() -> Any:
    """Stop energy module's data collection loop."""
    from app.modules.energy.scheduler import stop_energy_collection_flag

    stop_energy_collection_flag.set()


register_background_worker(
    name="energy.collection",
    start=_start_energy_collection,
    stop=_stop_energy_collection,
)
