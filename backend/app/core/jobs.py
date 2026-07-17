"""Task queue for user-triggered long-running operations.

TODO: Migrate to a proper task queue (e.g., Celery, ARQ) for retry, persistence,
and monitoring capabilities.
"""

from app.core.tasks import spawn_task

__all__ = ["spawn_task"]
