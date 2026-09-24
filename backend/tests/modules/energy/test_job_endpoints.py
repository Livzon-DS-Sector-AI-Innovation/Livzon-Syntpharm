"""API tests for energy's job endpoints.

These are the endpoints the shared job primitive replaced the module's hand-rolled
create/spawn/complete/fail lifecycle with, so they lock the observable contract: a sync
request returns a running job id, and the job-status endpoint reports the outcome.
"""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

_SYNC_TARGET = "app.modules.energy.bitable_sync.EnergyBitableSync"


def fake_bitable_sync(
    *,
    result: dict[str, int] | None = None,
    error: Exception | None = None,
) -> type:
    """A stand-in for the Feishu sync service: no network, no writes."""

    class _FakeBitableSync:
        async def sync_all(self, db: object) -> dict[str, int]:
            if error is not None:
                raise error
            return result if result is not None else {"synced": 2}

    return _FakeBitableSync


async def wait_for_terminal_status(client: AsyncClient, job_id: str) -> dict[str, object]:
    """Poll the job endpoint until the job leaves the running state."""
    for _ in range(200):
        await asyncio.sleep(0.01)
        response = await client.get(f"/api/v1/energy/jobs/{job_id}")
        assert response.status_code == 200
        job: dict[str, object] = response.json()["data"]
        if job["status"] != "running":
            return job
    raise AssertionError(f"job {job_id} never finished")


async def test_sync_returns_a_running_job_that_completes(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_SYNC_TARGET, fake_bitable_sync())

    response = await auth_client.post("/api/v1/energy/sync/bitable")

    assert response.status_code == 200
    started = response.json()["data"]
    assert started["status"] == "running"
    assert started["job_id"]

    job = await wait_for_terminal_status(auth_client, started["job_id"])
    assert job["status"] == "done"
    assert job["result"] == {"synced": 2}


async def test_a_failing_sync_leaves_a_failed_job_with_its_message(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_SYNC_TARGET, fake_bitable_sync(error=RuntimeError("feishu down")))

    response = await auth_client.post("/api/v1/energy/sync/bitable")
    job_id = response.json()["data"]["job_id"]

    job = await wait_for_terminal_status(auth_client, job_id)
    assert job["status"] == "failed"
    assert job["error"] == "feishu down"


async def test_an_unknown_job_is_not_found(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/energy/jobs/does-not-exist")

    assert response.status_code == 404
