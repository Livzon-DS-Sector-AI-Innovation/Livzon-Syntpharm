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


# Every route in the module that requires authentication, so a future edit cannot
# quietly drop the dependency. `AGENTS.md:166` allows a null user only on endpoints
# explicitly marked public, and none of these are.
#
# Nineteen gained `current_user: RequiredUser` in #96. The twentieth,
# `POST /hplc-reference/{id}/use`, already had it — asserted here too, because the
# point is the requirement rather than the diff.
#
# Routes authenticating via `Depends(_user_id)` are not listed: that helper takes
# `RequiredUser` itself, so they sit behind the same gate.
UNAUTHENTICATED_ROUTES = [
    ("GET", f"{BASE}/dict/nonexistent_dict"),  # /dict/{dict_type}
    ("GET", f"{BASE}/storage-condition/options"),  # /storage-condition/options
    ("GET", f"{BASE}/unit/options"),  # /unit/options
    ("GET", f"{BASE}/hplc-reference/template"),  # /hplc-reference/template
    ("GET", f"{BASE}/hplc-reference"),  # /hplc-reference
    ("GET", f"{BASE}/hplc-reference/need-recal"),  # /hplc-reference/need-recal
    ("GET", f"{BASE}/hplc-reference/1"),  # /hplc-reference/{id}
    ("DELETE", f"{BASE}/hplc-reference/1"),  # /hplc-reference/{id}
    ("POST", f"{BASE}/hplc-reference/1/use"),  # /hplc-reference/{id}/use
    ("GET", f"{BASE}/hplc-reference/1/usage-history"),  # /hplc-reference/{id}/usage-history
    ("GET", f"{BASE}/chrom-column"),  # /chrom-column
    ("GET", f"{BASE}/chrom-column/template"),  # /chrom-column/template
    ("GET", f"{BASE}/chrom-column/1"),  # /chrom-column/{id}
    ("DELETE", f"{BASE}/chrom-column/1"),  # /chrom-column/{id}
    ("GET", f"{BASE}/medium"),  # /medium
    ("GET", f"{BASE}/medium/1"),  # /medium/{id}
    ("GET", f"{BASE}/standard"),  # /standard
    ("GET", f"{BASE}/standard/1"),  # /standard/{id}
    ("GET", f"{BASE}/storage-condition"),  # /storage-condition
    ("GET", f"{BASE}/storage-condition/1"),  # /storage-condition/{id}
]


@pytest.mark.parametrize(("method", "path"), UNAUTHENTICATED_ROUTES)
async def test_endpoints_require_auth(anonymous_client: AsyncClient, method: str, path: str) -> None:
    """A request with no token is rejected, rather than served.

    Before this, these routes declared no user dependency at all, so they were
    reachable without authenticating — including the DELETE. This asserts the
    gate exists; it does not care which status the framework picks beyond 401.
    """
    response = await anonymous_client.request(method, path)

    assert response.status_code == 401, f"{method} {path} returned {response.status_code} without a token; expected 401"


async def test_unknown_dictionary_returns_404(auth_client: AsyncClient) -> None:
    """A read for something that does not exist answers 404.

    Deliberately uses the dictionary route rather than a by-id one: the by-id routes
    declare `id: int` against a uuid primary key, so they fail on a Postgres cast
    before reaching their not-found branch. That defect is tracked separately; this
    test pins the status-code contract on a route that can actually reach it.

    Before this, the route returned HTTP 200 carrying `code: 404` in the body, so a
    client checking the status code saw success.
    """
    response = await auth_client.get(f"{BASE}/dict/definitely_not_a_dict_type")

    assert response.status_code == 404, (
        f"expected 404 for an unknown dictionary type, got {response.status_code}: {response.text}"
    )


async def test_read_by_id_round_trips(auth_client: AsyncClient) -> None:
    """A record can be fetched by the id it was created with.

    This exercises the route rather than only its auth gate. The by-id routes declared
    `id: int` while the primary key is a uuid, so Postgres rejected the cast before the
    lookup — every by-id route was unreachable, and asserting 401 never reached it.
    """
    created = await _create_hplc_reference(auth_client)
    record_id = created["id"]
    uuid.UUID(record_id)  # the id is a uuid, not an integer

    response = await auth_client.get(f"{BASE}/hplc-reference/{record_id}")
    assert response.status_code == 200, response.text

    fetched = response.json()["data"]
    assert fetched["id"] == record_id
    assert fetched["ref_code"] == created["ref_code"]


async def test_read_by_id_missing_record_returns_404(auth_client: AsyncClient) -> None:
    """A by-id read for an id that does not exist answers 404.

    A random uuid parses at the routing layer and reaches the service, which is what
    the 404 contract is for. Before the annotation fix this never got that far.
    """
    response = await auth_client.get(f"{BASE}/hplc-reference/{uuid.uuid4()}")

    assert response.status_code == 404, response.text


async def test_duplicate_create_returns_400(auth_client: AsyncClient) -> None:
    """A write the service rejects answers 400.

    The service raises `ValueError` for a duplicate reference code. That was caught and
    returned as `code: 400` inside a 200, so the failure was invisible to the caller.
    """
    body = {"ref_code": f"REF-{uuid.uuid4().hex[:8]}", "ref_name": "重复校验"}

    first = await auth_client.post(f"{BASE}/hplc-reference", json=body)
    assert first.status_code == 200, first.text

    duplicate = await auth_client.post(f"{BASE}/hplc-reference", json=body)
    assert duplicate.status_code == 400, f"expected 400 for a duplicate, got {duplicate.status_code}: {duplicate.text}"


async def _create_hplc_reference(auth_client: AsyncClient, extra: dict | None = None) -> dict:
    code = f"REF-{uuid.uuid4().hex[:8]}"
    body = {"ref_code": code, "ref_name": "对照品测试", **(extra or {})}
    response = await auth_client.post(f"{BASE}/hplc-reference", json=body)
    assert response.status_code == 200, response.text
    return response.json()["data"]
