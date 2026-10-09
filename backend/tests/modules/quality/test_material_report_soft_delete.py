"""Deleting a material report soft-deletes it.

`AGENTS.md:130` makes soft delete the default — 不做物理删除（除非需求明确要求）—
and no such requirement exists. `MaterialReportRepository.delete()` was the only
hard delete in the module, while `ReportTemplateRepository.delete()` beside it
soft-deleted.

These tests exist because the first version of this file passed *without running*:
it skipped a step on a wrong URL and returned early, so both tests went green while
the endpoint was still hard-deleting. Only reverting the fix and re-running exposed
it — which is why the differential is noted in the commit.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

BASE = "/api/v1/quality/material-report"


async def _create_report(auth_client: AsyncClient) -> str:
    """Create a report and return its id.

    `template_id` is optional on `ReportCreate`, so no template fixture is needed.
    """
    created = await auth_client.post(
        f"{BASE}/",
        json={"report_title": "软删除测试报告单", "report_date": "2026-10-09"},
    )
    assert created.status_code == 200, f"create failed: {created.status_code} {created.text[:200]}"

    payload: dict[str, Any] = created.json()["data"]
    report_id: str = payload["id"]
    assert report_id, "create returned no id"
    return report_id


async def test_delete_soft_deletes_rather_than_removing_the_row(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    """The row survives the delete and is marked `is_deleted`.

    A physical delete removes it — and fires the `ondelete="CASCADE"` on
    `material_report_items` and `report_images`, taking the children silently.
    """
    report_id = await _create_report(auth_client)

    deleted = await auth_client.delete(f"{BASE}/{report_id}")
    assert deleted.status_code == 200, deleted.text

    from sqlalchemy import select

    from app.modules.quality.qms.material_report_models import MaterialReport

    row = (await db_session.execute(select(MaterialReport).where(MaterialReport.id == report_id))).scalar_one_or_none()

    assert row is not None, "the row was physically deleted — AGENTS.md:130 requires soft delete"
    assert row.is_deleted is True, "the row survived but was not marked is_deleted"


async def test_deleted_report_leaves_the_list(auth_client: AsyncClient) -> None:
    """...and does not linger in the list.

    The list query gained an `is_deleted` filter in the same change. Without a test
    it would be untested behaviour — and a soft delete that still shows the row is
    worse than a hard delete, because the row stays visible while the code claims
    it is gone.
    """
    report_id = await _create_report(auth_client)

    async def ids_in_list() -> set[str]:
        response = await auth_client.get(f"{BASE}/")
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return {item["id"] for item in (body["data"]["items"] or [])}

    assert report_id in await ids_in_list(), "the new report is missing from the list before delete"

    await auth_client.delete(f"{BASE}/{report_id}")

    assert report_id not in await ids_in_list(), "a soft-deleted report is still listed"


async def test_deleted_report_is_no_longer_readable(auth_client: AsyncClient) -> None:
    """A soft delete that still returns the record would be cosmetic."""
    report_id = await _create_report(auth_client)

    before = await auth_client.get(f"{BASE}/{report_id}")
    assert before.status_code == 200, before.text

    await auth_client.delete(f"{BASE}/{report_id}")

    after = await auth_client.get(f"{BASE}/{report_id}")
    assert after.status_code == 404, (
        f"a soft-deleted report is still readable ({after.status_code}) — "
        "the query filters are missing, so the delete is only cosmetic"
    )
