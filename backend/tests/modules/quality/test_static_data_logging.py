"""A failed bulk import records a traceback.

Before this, the import's failure path returned a message to the caller and logged
nothing, so a failed import left no trace anywhere. The module had no logger at all.
"""

from __future__ import annotations

import asyncio
import io
import logging

import openpyxl
import pytest
from httpx import AsyncClient

BASE = "/api/v1/quality/static-data"

# The logger the module is expected to use — `logging.getLogger(__name__)` in
# `app.modules.quality.qms.static_data.api`.
MODULE_LOGGER = "app.modules.quality.qms.static_data.api"


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


async def test_failed_import_logs_a_traceback(
    auth_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Malformed workbook: the handler answers, and logs the exception.

    The response alone is not enough to diagnose a failed import — the caller sees
    a message, but an operator reading logs sees nothing. `exc_info` is the point:
    a bare message would not carry the stack.
    """
    # Valid extension, invalid content: passes the filename guard, then openpyxl
    # raises when it tries to read the workbook.
    bad_file = ("ref.xlsx", io.BytesIO(b"this is not a spreadsheet"), "application/vnd.ms-excel")

    with caplog.at_level(logging.ERROR, logger=MODULE_LOGGER):
        response = await auth_client.post(f"{BASE}/hplc-reference/batch-import", files={"file": bad_file})

        # The import is a job now (#100), so the handler answers **202 immediately**
        # and the failure happens off-request. The status assertion moved with it,
        # and the log only appears once the worker has run — so wait for the job to
        # leave `running` rather than sampling the log straight away.
        assert response.status_code == 202, response.text
        job_id = response.json()["data"]["job_id"]

        for _ in range(50):
            poll = await auth_client.get(f"{BASE}/jobs/{job_id}")
            if poll.json()["data"]["status"] != "running":
                break
            await asyncio.sleep(0.1)

    records = [r for r in caplog.records if r.name == MODULE_LOGGER]
    assert records, (
        f"the failing import logged nothing on {MODULE_LOGGER!r}; captured: {[r.name for r in caplog.records]}"
    )

    with_traceback = [r for r in records if r.exc_info]
    assert with_traceback, (
        f"the import failure was logged without exc_info, so no stack was recorded: {[r.getMessage() for r in records]}"
    )


async def test_row_level_failure_is_logged(
    auth_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    """A single bad row is logged, not only a corrupt whole file.

    The corrupt-workbook test above covers the rare case — the file will not open
    at all. The *ordinary* failed import is one row the database rejects while the
    rest succeed: those are caught per-row and collected into the response, and
    before this they were logged nowhere. An operator saw "1 failed" and had no way
    to find which row or why.
    """
    # A duplicate ref_code: the first row inserts, the second is refused by the
    # service's uniqueness check. One success, one failure — the ordinary case.
    payload = _workbook([("REF-DUP", "对照品甲", "10mg"), ("REF-DUP", "对照品乙", "20mg")])
    bad_file = ("dup.xlsx", io.BytesIO(payload), "application/vnd.ms-excel")

    with caplog.at_level(logging.WARNING, logger=MODULE_LOGGER):
        response = await auth_client.post(f"{BASE}/hplc-reference/batch-import", files={"file": bad_file})
        assert response.status_code == 202, response.text
        job_id = response.json()["data"]["job_id"]

        for _ in range(50):
            poll = await auth_client.get(f"{BASE}/jobs/{job_id}")
            if poll.json()["data"]["status"] != "running":
                break
            await asyncio.sleep(0.1)

    row_logs = [r for r in caplog.records if "row failed" in r.getMessage()]
    assert row_logs, (
        "a rejected row was never logged; the caller is told a count and nothing more. "
        f"captured: {[r.getMessage() for r in caplog.records]}"
    )
    # The row number is the thing an operator needs to fix the sheet.
    assert any(getattr(r, "row", None) for r in row_logs), "the log line does not carry the row number"
