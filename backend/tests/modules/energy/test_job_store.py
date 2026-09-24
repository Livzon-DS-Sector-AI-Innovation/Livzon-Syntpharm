"""Behaviour-preservation tests for the energy job store.

The module's job state now lives in the core primitive, so these tests lock the shape its
API promised before the move: `create()` returns a job id, `get()` returns a mapping with
exactly status/result/error/created_at, and the status strings are unchanged.
"""

from __future__ import annotations

from app.modules.energy.job_store import JobStore, sync_job_store

LEGACY_KEYS = {"status", "result", "error", "created_at"}


def test_create_returns_an_id_and_a_running_legacy_record() -> None:
    store = JobStore()

    job_id = store.create()
    job = store.get(job_id)

    assert isinstance(job_id, str)
    assert job is not None
    assert set(job) == LEGACY_KEYS
    assert job["status"] == "running"
    assert job["result"] is None
    assert job["error"] is None
    assert isinstance(job["created_at"], float)


def test_complete_and_fail_keep_the_legacy_status_strings() -> None:
    store = JobStore()

    done = store.create()
    store.complete(done, {"ok": True})
    assert store.get(done)["status"] == "done"  # type: ignore[index]
    assert store.get(done)["result"] == {"ok": True}  # type: ignore[index]

    failed = store.create()
    store.fail(failed, "boom")
    assert store.get(failed)["status"] == "failed"  # type: ignore[index]
    assert store.get(failed)["error"] == "boom"  # type: ignore[index]


def test_unknown_job_returns_none() -> None:
    assert JobStore().get("missing") is None


def test_the_module_singleton_is_a_job_store() -> None:
    assert isinstance(sync_job_store, JobStore)
    assert sync_job_store.get("missing") is None
