# mypy: ignore-errors
"""Tests for the deviation API auth contract.

AGENTS.md requires every business endpoint to declare an explicit auth
dependency; the deviation endpoints that had none now require a user.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

PROTECTED_ENDPOINTS = [
    ("get", "/api/v1/quality/deviation", None),
    ("delete", "/api/v1/quality/deviation/{deviation_id}", None),
    ("post", "/api/v1/quality/deviation/{deviation_id}/lock-batch", {}),
    ("post", "/api/v1/quality/deviation/{deviation_id}/unlock-batch", {}),
    ("get", "/api/v1/quality/deviation/investigations/list", None),
    ("post", "/api/v1/quality/deviation/{deviation_id}/investigation", {}),
    ("put", "/api/v1/quality/deviation/{deviation_id}/investigation", {}),
    ("post", "/api/v1/quality/deviation/{deviation_id}/investigation/complete", {}),
    ("get", "/api/v1/quality/deviation/corrections/list", None),
    ("post", "/api/v1/quality/deviation/{deviation_id}/correction", {}),
    ("put", "/api/v1/quality/deviation/{deviation_id}/correction", {}),
    ("post", "/api/v1/quality/deviation/{deviation_id}/correction/progress?progress=50", {}),
    ("get", "/api/v1/quality/deviation/closings/list", None),
    ("post", "/api/v1/quality/deviation/{deviation_id}/closing", {}),
    ("put", "/api/v1/quality/deviation/{deviation_id}/closing", {}),
    ("post", "/api/v1/quality/deviation/{deviation_id}/closing/complete", {}),
]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    PROTECTED_ENDPOINTS,
    ids=[f"{method.upper()} {path}" for method, path, _ in PROTECTED_ENDPOINTS],
)
async def test_deviation_endpoints_require_auth(
    anonymous_client: AsyncClient,
    method: str,
    path: str,
    body: dict | None,
) -> None:
    """Every business deviation endpoint rejects an anonymous caller with 401."""
    url = path.format(deviation_id=uuid.uuid4())
    response = await anonymous_client.request(method, url, json=body)
    assert response.status_code == 401, f"{method.upper()} {url} returned {response.status_code}"


async def test_deviation_list_allows_authenticated_user(auth_client: AsyncClient) -> None:
    """An authenticated caller still reaches the deviation list."""
    response = await auth_client.get("/api/v1/quality/deviation")
    assert response.status_code == 200
