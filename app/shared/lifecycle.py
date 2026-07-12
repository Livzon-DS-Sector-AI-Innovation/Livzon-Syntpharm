"""Background worker lifecycle management — auto-registration pattern.

Modules register their background workers (WebSocket clients, schedulers, etc.)
at import time. The main application auto-starts all registered workers without
manual wiring in main.py.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass
class BackgroundWorker:
    """A background worker that runs for the lifetime of the application."""

    name: str  # Unique identifier (e.g., "safety.ws_client")
    start: Callable[[], Awaitable[None]]  # Async function to start the worker
    stop: Callable[[], Awaitable[None]] | Callable[[], None] | None = None  # Optional graceful shutdown (sync or async)


# Global registry of background workers
_WORKERS: list[BackgroundWorker] = []


def register_background_worker(
    name: str,
    start: Callable[[], Awaitable[None]],
    stop: Callable[[], Awaitable[None]] | Callable[[], None] | None = None,
) -> None:
    """Register a background worker to be auto-started by the application.

    Args:
        name: Unique identifier for the worker (e.g., "safety.ws_client")
        start: Async function that starts the worker
        stop: Optional function for graceful shutdown (can be sync or async)

    Example:
        # In app/modules/safety/__init__.py
        from app.shared.lifecycle import register_background_worker

        async def _start_safety_ws():
            from app.modules.safety.feishu.event_client import start_ws
            await start_ws()

        register_background_worker("safety.ws_client", _start_safety_ws)
    """
    # Check for duplicate names
    if any(w.name == name for w in _WORKERS):
        raise ValueError(f"Background worker '{name}' is already registered")

    _WORKERS.append(BackgroundWorker(name=name, start=start, stop=stop))


def get_all_workers() -> list[BackgroundWorker]:
    """Get all registered background workers."""
    return list(_WORKERS)


def clear_workers_registry() -> None:
    """Clear the worker registry (useful for testing)."""
    _WORKERS.clear()
