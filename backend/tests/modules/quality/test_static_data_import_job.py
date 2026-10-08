"""The batch import runs as a job and reports through a pollable status.

`AGENTS.md:310` forbids an operation over 5 seconds inside an HTTP request; the
import does one database round-trip per row, so it was moved off the request path.
"""

from __future__ import annotations

import asyncio
import io
from typing import Any

import openpyxl
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

BASE = "/api/v1/quality/static-data"


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


class _SessionCtx:
    """Hands the test's session to code that would open its own."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *exc: object) -> bool:
        return False


async def test_import_returns_a_job_and_polls_to_done(
    auth_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The endpoint answers 202 with a job id, and the job reports its counts.

    Before this the endpoint answered 200 only after every row was written.

    The worker normally opens its own session, which cannot see the test user —
    the fixture creates it with `flush`, and the conftest rolls the transaction
    back at teardown, so it is never committed. Pointing the module's factory at
    the test's session keeps the job on the same transaction, which is what makes
    the counts observable. The job mechanism itself is unchanged.
    """
    from app.modules.quality.qms.static_data import api as static_data_api

    monkeypatch.setattr(static_data_api, "async_session_factory", lambda: _SessionCtx(db_session))
    payload = _workbook([("REF-A", "对照品甲", "10mg"), ("REF-B", "对照品乙", "20mg")])

    response = await auth_client.post(
        f"{BASE}/hplc-reference/batch-import",
        files={"file": ("ref.xlsx", io.BytesIO(payload), "application/vnd.ms-excel")},
    )

    assert response.status_code == 202, f"expected 202 Accepted, got {response.status_code}: {response.text}"
    job_id = response.json()["data"]["job_id"]
    assert job_id

    # Poll until the job leaves `running`. Bounded, so a stuck job fails rather
    # than hanging the suite.
    status: str | None = None
    body: dict[str, Any] | None = None
    for _ in range(50):
        poll = await auth_client.get(f"{BASE}/jobs/{job_id}")
        assert poll.status_code == 200, poll.text
        body = poll.json()["data"]
        status = body["status"]
        if status != "running":
            break
        await asyncio.sleep(0.2)

    assert status == "done", f"job did not finish: {body}"
    assert body is not None, "no job body was ever returned"
    assert body["result"]["success"] == 2, f"expected both rows imported: {body}"
    assert body["result"]["failed"] == 0


async def test_chrom_column_import_is_also_a_job(
    auth_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The chrom-column import follows the same 202-and-poll contract.

    Asserted separately because the two handlers are separate code paths; one being
    converted says nothing about the other.
    """
    from app.modules.quality.qms.static_data import api as static_data_api

    monkeypatch.setattr(static_data_api, "async_session_factory", lambda: _SessionCtx(db_session))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["色谱柱编号*", "色谱柱类型*", "序列号S.N*", "存放位置*", "贮存条件编码*", "验收日期*"])
    ws.append(["COL-1", "C18", "SN-1", "液相室A柜", "ROOM_TEMP", "2024-05-04"])
    buf = io.BytesIO()
    wb.save(buf)

    response = await auth_client.post(
        f"{BASE}/chrom-column/batch-import",
        files={"file": ("col.xlsx", io.BytesIO(buf.getvalue()), "application/vnd.ms-excel")},
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["data"]["job_id"]

    status: str | None = None
    body: dict[str, Any] | None = None
    for _ in range(50):
        poll = await auth_client.get(f"{BASE}/jobs/{job_id}")
        body = poll.json()["data"]
        status = body["status"]
        if status != "running":
            break
        await asyncio.sleep(0.2)

    assert status == "done", f"job did not finish: {body}"
    assert body is not None, "no job body was ever returned"
    assert body["result"]["success"] == 1, f"expected the row imported: {body}"


async def test_unknown_job_returns_404(auth_client: AsyncClient) -> None:
    """Polling an id the store does not hold answers 404, not an empty 200.

    The store is in memory, so an id from a previous process is genuinely unknown —
    which is exactly the case a poller has to handle.
    """
    response = await auth_client.get(f"{BASE}/jobs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404, response.text
