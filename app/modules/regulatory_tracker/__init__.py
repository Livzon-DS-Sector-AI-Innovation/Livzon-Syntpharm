"""Regulatory Tracker Module - 法规自动监控追踪系统"""

from app.modules.regulatory_tracker.api import router
from app.shared.lifecycle import register_background_worker

__all__ = ["router"]


# ── Background worker registration ────────────────────────────


async def _start_regulatory_scheduler():
    """Start regulatory tracker's APScheduler."""
    from app.modules.regulatory_tracker.tasks.sync_tasks import start_scheduler

    await start_scheduler()


async def _stop_regulatory_scheduler():
    """Stop regulatory tracker's APScheduler."""
    from app.modules.regulatory_tracker.tasks.sync_tasks import stop_scheduler

    stop_scheduler()


register_background_worker(
    name="regulatory_tracker.scheduler",
    start=_start_regulatory_scheduler,
    stop=_stop_regulatory_scheduler,
)
