"""A record can be fetched by the id it was created with.

Every by-id route in this module was unreachable: the path parameter was declared
as an integer while the primary key is a uuid, so Postgres rejected the comparison
before the lookup.

    WHERE qms.t_qs_hplc_reference.id = $1::INTEGER
    HINT:  No operator matches the given name and argument types.

An integer is refused by the database; a uuid is refused by the route. No input
worked, on any of the by-id routes.

These tests exist because type agreement is not the same as a working query. `mypy`
saw `int` matching `int` and `alembic check` saw `uuid` matching `uuid`; both passed
while the route was broken. Only executing it proves otherwise.
"""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient

BASE = "/api/v1/quality/static-data"


async def _create(auth_client: AsyncClient) -> dict[str, Any]:
    code = f"REF-{uuid.uuid4().hex[:8]}"
    response = await auth_client.post(
        f"{BASE}/hplc-reference",
        json={"ref_code": code, "ref_name": "对照品按 ID 读取"},
    )
    assert response.status_code == 200, response.text

    # `response.json()` is `Any`; narrow it so the declared return type is checked
    # rather than asserted. Same shape as the fix in test_static_data_api.py.
    payload = response.json()["data"]
    assert isinstance(payload, dict)
    return payload


async def test_read_by_id_round_trips(auth_client: AsyncClient) -> None:
    """A record is fetched by the id it was created with.

    Before the fix this answered 500: the uuid never reached the query.
    """
    created = await _create(auth_client)
    record_id = created["id"]

    # The id is a uuid, not an integer — that is the whole point.
    uuid.UUID(record_id)

    response = await auth_client.get(f"{BASE}/hplc-reference/{record_id}")
    assert response.status_code == 200, response.text

    fetched = response.json()["data"]
    assert fetched["id"] == record_id
    assert fetched["ref_code"] == created["ref_code"]


async def test_read_by_id_missing_record_returns_404(auth_client: AsyncClient) -> None:
    """An unknown id answers 404 — the contract, not a database error.

    A random uuid parses at the routing layer and reaches the service, which is
    where the not-found is decided. Before the fix it never got that far.
    """
    response = await auth_client.get(f"{BASE}/hplc-reference/{uuid.uuid4()}")

    assert response.status_code == 404, response.text
