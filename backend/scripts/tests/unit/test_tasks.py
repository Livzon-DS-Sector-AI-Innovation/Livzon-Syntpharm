# mypy: ignore-errors
"""Tests for app.core.tasks spawn_task utility."""

from __future__ import annotations

from app.core.tasks import spawn_task


async def test_spawn_task_success():
    """Test that spawn_task executes the coroutine successfully."""
    result = []

    async def test_coro():
        result.append("executed")

    task = spawn_task(test_coro(), name="test_task")
    await task

    assert result == ["executed"]


async def test_spawn_task_error_handling():
    """Test that spawn_task catches and logs exceptions."""

    async def failing_coro():
        raise ValueError("Test error")

    # Should not raise - errors are caught internally
    task = spawn_task(failing_coro(), name="failing_task")
    await task

    # Task should complete without raising
    assert task.done()


async def test_spawn_task_with_name():
    """Test that spawn_task accepts and uses custom names."""

    async def test_coro():
        pass

    task = spawn_task(test_coro(), name="custom_name")
    assert task.get_name() == "custom_name"
    await task


async def test_spawn_task_default_name():
    """Test that spawn_task generates default names."""

    async def test_coro():
        pass

    task = spawn_task(test_coro())
    assert task.get_name().startswith("task-")
    await task
