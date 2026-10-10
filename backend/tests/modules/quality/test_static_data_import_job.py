"""The batch import runs as a job, and the job's state is a durable row.

`AGENTS.md:310` forbids an operation over 5 seconds inside a request, so the rows are
created off-request. `AGENTS.md:308` adds that the work must not be `create_task`-only
— 无法重试、无法监控、重启后丢失 — so the job's state lives in `core.background_jobs`
rather than the in-memory dict this replaced.

## What these tests do and do not cover

They exercise `JobRepository` directly. That is the part that made the difference:
`create` / `complete` / `fail` / `get` are now row operations, and a row survives a
restart — which is the whole point of the change.

They do **not** drive the spawned worker end to end. The conftest isolates each test
in a transaction it rolls back, and creates its user with `flush`, never `commit`, so
a worker holding its own session cannot see that user — the FK on `created_by` fails.
An earlier version of this file worked around that by handing the worker the test's
own session; that is invalid now two coroutines would share one `AsyncSession`, which
is what `asyncpg` reports as "another operation is in progress". Rather than fake it,
the worker path is covered by CI's e2e run against a real committed database.
"""

from __future__ import annotations

import io
import uuid

import openpyxl
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.job_models import JOB_DONE, JOB_FAILED, JOB_RUNNING
from app.core.job_repository import JobRepository

BASE = "/api/v1/quality/static-data"

pytestmark = pytest.mark.usefixtures("db_session")


def _workbook(rows: list[tuple[object, ...]]) -> bytes:
    """A minimal .xlsx with the headers the importer expects."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["对照品编号(ref_code)*", "对照品名称(ref_name)*", "规格(spec)"])
    for r in rows:
        ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def test_create_writes_a_running_row(db_session: AsyncSession) -> None:
    """A new job is a row in `running`, and its id can be looked up."""
    repo = JobRepository(db_session)
    job_id = await repo.create("test-job")

    job = await repo.get(job_id)
    assert job is not None, "the job row was not written"
    assert job.state == JOB_RUNNING
    assert job.name == "test-job"
    assert job.started_at is not None, "a job must record when it started"
    assert job.finished_at is None


async def test_complete_records_the_result(db_session: AsyncSession) -> None:
    repo = JobRepository(db_session)
    job_id = await repo.create("test-job")

    await repo.complete(job_id, {"success": 2, "failed": 0})

    job = await repo.get(job_id)
    assert job is not None
    assert job.state == JOB_DONE
    assert job.result == {"success": 2, "failed": 0}
    assert job.finished_at is not None, "a finished job must record when"
    assert job.error is None


async def test_fail_records_the_error(db_session: AsyncSession) -> None:
    repo = JobRepository(db_session)
    job_id = await repo.create("test-job")

    await repo.fail(job_id, "row 14: bad date")

    job = await repo.get(job_id)
    assert job is not None
    assert job.state == JOB_FAILED
    assert job.error == "row 14: bad date"
    assert job.finished_at is not None


async def test_an_interrupted_job_is_findable(db_session: AsyncSession) -> None:
    """A job left `running` can be found — the reason for the table.

    The in-memory store could not express this: after a restart the job simply did
    not exist, so an interrupted import was indistinguishable from one that never
    ran. A `running` row that has a `started_at` and no `finished_at` is the signal.
    """
    repo = JobRepository(db_session)
    interrupted = await repo.create("test-job")
    finished = await repo.create("test-job")
    await repo.complete(finished, {"success": 1, "failed": 0})

    unfinished = await repo.list_unfinished()

    ids = {str(j.id) for j in unfinished}
    assert str(interrupted) in ids, "an interrupted job is not discoverable"
    assert str(finished) not in ids, "a finished job was reported as unfinished"


async def test_unknown_job_returns_none(db_session: AsyncSession) -> None:
    """A poller with a bad id gets nothing back, not an exception."""
    assert await JobRepository(db_session).get(uuid.uuid4()) is None


# --- the endpoint contract -------------------------------------------------
#
# These assert the 202-and-poll shape only. They do not wait for the worker, because
# the worker cannot run against this fixture — see the module docstring.


async def test_import_returns_a_job_handle(auth_client: AsyncClient) -> None:
    """The endpoint answers 202 with a job id, not a result.

    Before #100 it answered 200 only after every row was written.
    """
    payload = _workbook([("REF-A", "对照品甲", "10mg")])

    response = await auth_client.post(
        f"{BASE}/hplc-reference/batch-import",
        files={"file": ("ref.xlsx", io.BytesIO(payload), "application/vnd.ms-excel")},
    )

    assert response.status_code == 202, response.text
    job_id = response.json()["data"]["job_id"]
    assert job_id, "the response carried no job id"
    # The id must be a uuid the poll route can parse — it is a row key now.
    uuid.UUID(job_id)


async def test_unknown_job_returns_404(auth_client: AsyncClient) -> None:
    """A poll for an id that does not exist answers 404, not an empty 200."""
    response = await auth_client.get(f"{BASE}/jobs/{uuid.uuid4()}")
    assert response.status_code == 404, response.text


async def test_malformed_job_id_returns_404(auth_client: AsyncClient) -> None:
    """A non-uuid id is refused as not-found, not as a 500.

    The poll route parses the path segment into a UUID; anything else cannot name a
    row, so it is absent rather than an error.
    """
    response = await auth_client.get(f"{BASE}/jobs/not-a-uuid")
    assert response.status_code == 404, response.text
