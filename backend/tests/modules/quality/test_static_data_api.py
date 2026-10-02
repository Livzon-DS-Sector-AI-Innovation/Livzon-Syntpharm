# mypy: ignore-errors
"""Static-data API behaviour for the quality module.

Regression cover for the eleven tables migration 0033 dropped. Before the fix
their list endpoints returned HTTP 500 with an ``UndefinedTableError``. The
tests also pin the creator contract: it comes from the authenticated session,
never from the request body.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

BASE = "/api/v1/quality/static-data"

LIST_ENDPOINTS = [
    f"{BASE}/hplc-reference?page=1&page_size=20",
    f"{BASE}/chrom-column?page=1&page_size=20",
    f"{BASE}/medium?page=1&page_size=20",
    f"{BASE}/standard?page=1&page_size=20",
    f"{BASE}/storage-condition?page=1&page_size=20",
    # The two dictionary endpoints join the same tables and, before the fix,
    # failed with `AttributeError: type object has no attribute 'del_flag'`.
    f"{BASE}/storage-condition/options",
    f"{BASE}/unit/options",
]


@pytest.mark.parametrize("path", LIST_ENDPOINTS)
async def test_static_data_endpoints_return_200(auth_client: AsyncClient, path: str) -> None:
    """Every static-data read endpoint returns 200 rather than HTTP 500."""
    response = await auth_client.get(path)

    assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text}"


async def test_create_takes_creator_from_session(auth_client: AsyncClient) -> None:
    """Two creates share the session user as creator."""
    first = await _create_hplc_reference(auth_client)
    second = await _create_hplc_reference(auth_client)

    # Same session user -> same creator, on both records.
    assert first["created_by"] is not None
    assert first["created_by"] == second["created_by"]
    # And it is a UUID, because the column is now a UUID foreign key.
    uuid.UUID(first["created_by"])


async def test_create_ignores_body_supplied_creator(auth_client: AsyncClient) -> None:
    """A `create_by` sent in the body cannot override the session creator."""
    data = await _create_hplc_reference(auth_client, extra={"create_by": 0})

    # The legacy placeholder is not echoed, and the response is not `create_by: 0`.
    assert "create_by" not in data
    assert data["created_by"] != 0
    uuid.UUID(data["created_by"])


async def test_response_exposes_the_shared_audit_columns(auth_client: AsyncClient) -> None:
    """Responses carry the shared audit shape, not the legacy column names."""
    data = await _create_hplc_reference(auth_client)

    for shared in ("created_at", "created_by", "id"):
        assert shared in data, f"missing shared column {shared}"
    for legacy in ("create_by", "create_time", "update_time", "del_flag"):
        assert legacy not in data, f"legacy column {legacy} still exposed"


async def _create_hplc_reference(auth_client: AsyncClient, extra: dict | None = None) -> dict:
    code = f"REF-{uuid.uuid4().hex[:8]}"
    body = {"ref_code": code, "ref_name": "对照品测试", **(extra or {})}
    response = await auth_client.post(f"{BASE}/hplc-reference", json=body)
    assert response.status_code == 200, response.text
    return response.json()["data"]
