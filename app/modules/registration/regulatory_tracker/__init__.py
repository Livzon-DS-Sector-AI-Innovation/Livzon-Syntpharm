"""Regulatory Tracker Module - 法规自动监控追踪系统"""

from typing import Any

from app.modules.registration.regulatory_tracker.api import router
from app.shared.lifecycle import register_background_worker

__all__ = ["router"]


# ── Background worker registration ────────────────────────────


async def _start_regulatory_scheduler() -> Any:
    """Start regulatory tracker's scheduler."""
    from app.modules.registration.regulatory_tracker.tasks.sync_tasks import (
        run_scheduler,
        start_scheduler,
    )

    start_scheduler()
    await run_scheduler()


async def _stop_regulatory_scheduler() -> Any:
    """Stop regulatory tracker's scheduler."""
    from app.modules.registration.regulatory_tracker.tasks.sync_tasks import (  # type: ignore[attr-defined]
        stop_scheduler,
    )

    stop_scheduler()


register_background_worker(
    name="regulatory_tracker.scheduler",
    start=_start_regulatory_scheduler,
    stop=_stop_regulatory_scheduler,
)
