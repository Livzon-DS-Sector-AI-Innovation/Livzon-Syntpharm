"""Tests for the core job primitive.

Pure unit tests: no database, no HTTP, no model loading. The store is exercised through
its interface, and one test substitutes a second implementation to prove that callers
depend on the interface rather than on the in-memory class.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core.jobs import (
    DEFAULT_JOB_TIMEOUT_SECONDS,
    JOB_STATUS_DONE,
    JOB_STATUS_FAILED,
    JOB_STATUS_RUNNING,
    InMemoryJobStore,
    JobRecord,
    spawn_job,
)
from app.core.logging_config import request_id_var


class RecordingStore:
    """A second implementation of the store interface (no storage of its own)."""

    def __init__(self) -> None:
        self.created: list[JobRecord] = []
        self.completed: list[tuple[str, Any]] = []
        self.failed: list[tuple[str, str]] = []

    def create(
        self,
        *,
        timeout_seconds: float | None = DEFAULT_JOB_TIMEOUT_SECONDS,
        request_id: str | None = None,
    ) -> JobRecord:
        # Capture request_id from context if not explicitly provided
        if request_id is None:
            context_request_id = request_id_var.get()
            # Only use it if it's a real request ID (not the default "-")
            if context_request_id != "-":
                request_id = context_request_id
        
        record = JobRecord(
            job_id=f"job-{len(self.created)}",
            timeout_seconds=timeout_seconds,
            request_id=request_id,
        )
        self.created.append(record)
        return record

    def get(self, job_id: str) -> JobRecord | None:
        return next((record for record in self.created if record.job_id == job_id), None)

    def complete(self, job_id: str, result: Any = None) -> None:
        self.completed.append((job_id, result))

    def fail(self, job_id: str, error: str) -> None:
        self.failed.append((job_id, error))

    def set_progress(self, job_id: str, progress: float) -> None:
        record = self.get(job_id)
        if record is not None:
            record.progress = progress


class TestInMemoryJobStore:
    def test_create_returns_a_running_record_with_start_time_and_timeout(self) -> None:
        store = InMemoryJobStore()
        before = time.time()

        record = store.create(timeout_seconds=42.0)

        assert record.job_id
        assert record.status == JOB_STATUS_RUNNING
        assert record.timeout_seconds == 42.0
        assert record.started_at is not None
        assert record.started_at >= before
        assert record.progress == 0.0
        assert record.result is None
        assert record.error is None
        assert record.request_id is None

    def test_get_returns_the_record_and_none_for_an_unknown_id(self) -> None:
        store = InMemoryJobStore()
        record = store.create()

        assert store.get(record.job_id) is record
        assert store.get("missing") is None

    def test_complete_marks_the_job_done_with_its_result(self) -> None:
        store = InMemoryJobStore()
        record = store.create()

        store.complete(record.job_id, {"rows": 3})

        assert record.status == JOB_STATUS_DONE
        assert record.result == {"rows": 3}
        assert record.progress == 1.0
        assert record.finished_at is not None

    def test_fail_marks_the_job_failed_with_its_error(self) -> None:
        store = InMemoryJobStore()
        record = store.create()

        store.fail(record.job_id, "boom")

        assert record.status == JOB_STATUS_FAILED
        assert record.error == "boom"
        assert record.finished_at is not None

    def test_progress_is_clamped_to_the_unit_interval(self) -> None:
        store = InMemoryJobStore()
        record = store.create()

        store.set_progress(record.job_id, 1.5)
        assert record.progress == 1.0

        store.set_progress(record.job_id, -2.0)
        assert record.progress == 0.0

        store.set_progress(record.job_id, 0.25)
        assert record.progress == 0.25

    def test_unknown_jobs_are_tolerated_by_every_mutator(self) -> None:
        """Mutations on an unknown id are no-ops, not errors."""
        store = InMemoryJobStore()

        store.complete("missing", 1)
        store.fail("missing", "x")
        store.set_progress("missing", 0.5)

        assert store.get("missing") is None


async def wait_for_task(record: JobRecord) -> None:
    """Await the job's background task. `spawn_job` always sets it."""
    assert record.task is not None
    await record.task


class TestSpawnJob:
    async def test_spawn_job_runs_the_work_and_records_the_result(self) -> None:
        store = InMemoryJobStore()

        async def work(record: JobRecord) -> str:
            store.set_progress(record.job_id, 0.5)
            return "done-value"

        record = spawn_job(store, work, name="unit-job")

        assert record.task is not None
        await wait_for_task(record)

        assert record.status == JOB_STATUS_DONE
        assert record.result == "done-value"
        assert record.task.get_name() == "unit-job"

    async def test_spawn_job_records_a_failure_without_raising(self) -> None:
        store = InMemoryJobStore()

        async def work(record: JobRecord) -> None:
            raise RuntimeError("worker blew up")

        record = spawn_job(store, work)
        await wait_for_task(record)

        assert record.status == JOB_STATUS_FAILED
        assert record.error == "worker blew up"

    async def test_the_job_stays_running_until_the_work_finishes(self) -> None:
        store = InMemoryJobStore()
        release = asyncio.Event()

        async def work(record: JobRecord) -> str:
            await release.wait()
            return "late"

        record = spawn_job(store, work)
        await asyncio.sleep(0)
        assert record.status == JOB_STATUS_RUNNING

        release.set()
        await wait_for_task(record)
        assert record.status == JOB_STATUS_DONE

    async def test_spawn_job_enforces_the_timeout(self) -> None:
        store = InMemoryJobStore()
        cancelled = asyncio.Event()

        async def work(record: JobRecord) -> str:
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                cancelled.set()
                raise
            return "never"

        record = spawn_job(store, work, timeout_seconds=0.05)
        await wait_for_task(record)

        assert record.status == JOB_STATUS_FAILED
        assert "timed out" in (record.error or "")
        assert cancelled.is_set()

    async def test_work_raising_its_own_timeout_error_keeps_its_message(self) -> None:
        """Our timeout is distinct from a TimeoutError raised inside the work."""
        store = InMemoryJobStore()

        async def work(record: JobRecord) -> None:
            raise TimeoutError("upstream stalled")

        record = spawn_job(store, work)
        await wait_for_task(record)

        assert record.status == JOB_STATUS_FAILED
        assert record.error == "upstream stalled"

    async def test_work_without_a_timeout_is_not_cancelled(self) -> None:
        store = InMemoryJobStore()

        async def work(record: JobRecord) -> str:
            await asyncio.sleep(0.01)
            return "finished"

        record = spawn_job(store, work, timeout_seconds=None)
        await wait_for_task(record)

        assert record.status == JOB_STATUS_DONE
        assert record.result == "finished"

    async def test_spawn_job_works_with_any_store_implementation(self) -> None:
        """The primitive depends on the interface, not on the in-memory class.

        The store owns the job's state, so this asserts the calls the primitive makes.
        """
        store = RecordingStore()

        async def work(record: JobRecord) -> int:
            return 7

        record = spawn_job(store, work)
        await wait_for_task(record)

        assert store.completed == [(record.job_id, 7)]
        assert store.failed == []


class TestRequestIdPropagation:
    """Tests for request_id support in the job primitive.

    The request_id is captured when the job is spawned and must be available
    throughout the job's lifecycle, even when the context changes.
    """

    def test_create_captures_request_id_from_context(self) -> None:
        """The job record captures the request_id from the context variable."""
        store = InMemoryJobStore()
        token = request_id_var.set("test-request-123")
        try:
            record = store.create()
            assert record.request_id == "test-request-123"
        finally:
            request_id_var.reset(token)

    def test_create_with_explicit_request_id_overrides_context(self) -> None:
        """An explicit request_id parameter takes precedence over the context."""
        store = InMemoryJobStore()
        token = request_id_var.set("context-request")
        try:
            record = store.create(request_id="explicit-request")
            assert record.request_id == "explicit-request"
        finally:
            request_id_var.reset(token)

    def test_create_without_request_id_in_context_is_none(self) -> None:
        """If no request_id is in context and none is provided, it's None."""
        store = InMemoryJobStore()
        token = request_id_var.set("-")
        try:
            record = store.create()
            assert record.request_id is None
        finally:
            request_id_var.reset(token)

    async def test_spawn_job_captures_request_id(self) -> None:
        """spawn_job captures the request_id and stores it on the record."""
        store = InMemoryJobStore()
        token = request_id_var.set("spawn-request-456")
        try:
            async def work(record: JobRecord) -> str:
                return "done"

            record = spawn_job(store, work)
            await wait_for_task(record)

            assert record.request_id == "spawn-request-456"
        finally:
            request_id_var.reset(token)

    async def test_request_id_available_in_work_function(self) -> None:
        """The work function can access the request_id from the record."""
        store = InMemoryJobStore()
        token = request_id_var.set("work-request-789")
        captured_request_id = None

        try:
            async def work(record: JobRecord) -> str:
                nonlocal captured_request_id
                captured_request_id = record.request_id
                return "done"

            record = spawn_job(store, work)
            await wait_for_task(record)

            assert captured_request_id == "work-request-789"
        finally:
            request_id_var.reset(token)

    async def test_request_id_persists_through_context_changes(self) -> None:
        """The request_id remains available even if the context changes during execution."""
        store = InMemoryJobStore()
        token = request_id_var.set("original-request")
        captured_ids = []

        try:
            async def work(record: JobRecord) -> str:
                captured_ids.append(record.request_id)
                # Change the context
                inner_token = request_id_var.set("different-request")
                try:
                    captured_ids.append(record.request_id)
                    await asyncio.sleep(0.001)
                    captured_ids.append(record.request_id)
                finally:
                    request_id_var.reset(inner_token)
                return "done"

            record = spawn_job(store, work)
            await wait_for_task(record)

            # All three captures should have the original request_id
            assert all(rid == "original-request" for rid in captured_ids)
        finally:
            request_id_var.reset(token)

    def test_recording_store_supports_request_id(self) -> None:
        """The RecordingStore test double also supports request_id."""
        store = RecordingStore()
        token = request_id_var.set("recording-request")
        try:
            record = store.create()
            assert record.request_id == "recording-request"
        finally:
            request_id_var.reset(token)
