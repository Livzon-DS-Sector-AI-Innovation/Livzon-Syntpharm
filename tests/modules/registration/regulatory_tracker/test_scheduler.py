"""Tests for regulatory_tracker SchedulerEngine integration."""

from __future__ import annotations

from app.modules.registration.regulatory_tracker.tasks.sync_tasks import (
    daily_ai_analysis_task,
    daily_sync_task,
)
from app.platform.scheduler import ScheduleStrategy


def test_daily_sync_task_definition():
    """Verify daily_sync_task is properly defined."""
    assert daily_sync_task.name == "regulatory_tracker.daily_sync"
    assert daily_sync_task.schedule.strategy == ScheduleStrategy.CRON
    assert daily_sync_task.schedule.expression == "0 2 * * *"
    assert daily_sync_task.module == "regulatory_tracker"
    assert daily_sync_task.timeout_seconds == 600


def test_daily_ai_analysis_task_definition():
    """Verify daily_ai_analysis_task is properly defined."""
    assert daily_ai_analysis_task.name == "regulatory_tracker.daily_ai_analysis"
    assert daily_ai_analysis_task.schedule.strategy == ScheduleStrategy.CRON
    assert daily_ai_analysis_task.schedule.expression == "0 3 * * *"
    assert daily_ai_analysis_task.module == "regulatory_tracker"
    assert daily_ai_analysis_task.timeout_seconds == 600


def test_tasks_are_callable():
    """Verify task coroutines are callable."""
    assert callable(daily_sync_task.coro)
    assert callable(daily_ai_analysis_task.coro)
