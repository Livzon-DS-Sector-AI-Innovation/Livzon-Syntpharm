from typing import Any

from app.platform.identity.models import Department, FeishuConfig, User
from app.shared.lifecycle import register_background_worker

__all__ = ["Department", "FeishuConfig", "User"]


# ── Background worker registration ────────────────────────────


async def _start_member_sync() -> Any:
    """Start identity module's member sync loop."""
    from app.platform.identity.scheduler import member_sync_loop

    await member_sync_loop()


async def _stop_member_sync() -> Any:
    """Stop identity module's member sync loop."""
    from app.platform.identity.scheduler import stop_member_sync_flag

    stop_member_sync_flag.set()


register_background_worker(
    name="identity.member_sync",
    start=_start_member_sync,
    stop=_stop_member_sync,
)
