"""偏差台账 API 契约测试。"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

PROTECTED_ENDPOINTS: list[tuple[str, str, dict[str, object] | None]] = [
    ("get", "/api/v1/quality/deviation/ledger", None),
    ("get", "/api/v1/quality/deviation/ledger/statistics", None),
    ("get", "/api/v1/quality/deviation/ledger/department-options", None),
    ("get", "/api/v1/quality/deviation/ledger/department-contact-options", None),
    ("get", "/api/v1/quality/deviation/ledger/investigator-options", None),
    ("get", "/api/v1/quality/deviation/ledger/status-options", None),
    ("get", "/api/v1/quality/deviation/ledger/jobs/{job_id}", None),
    ("get", "/api/v1/quality/deviation/ledger/{ledger_id}", None),
    ("post", "/api/v1/quality/deviation/ledger", {}),
    ("post", "/api/v1/quality/deviation/ledger/{ledger_id}/investigation-submit", {}),
    ("post", "/api/v1/quality/deviation/ledger/{ledger_id}/investigation-drafts", {}),
    ("delete", "/api/v1/quality/deviation/ledger/{ledger_id}/investigation-drafts", None),
    ("post", "/api/v1/quality/deviation/ledger/{ledger_id}/cross-dept-investigation", {}),
    ("post", "/api/v1/quality/deviation/ledger/{ledger_id}/cross-dept-review/reject", {}),
]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    PROTECTED_ENDPOINTS,
    ids=[f"{method.upper()} {path}" for method, path, _ in PROTECTED_ENDPOINTS],
)
async def test_ledger_endpoints_require_auth(
    anonymous_client: AsyncClient,
    method: str,
    path: str,
    body: dict[str, object] | None,
) -> None:
    """未登录一律 401。"""
    url = path.format(ledger_id=uuid.uuid4(), job_id=uuid.uuid4())
    response = await anonymous_client.request(method, url, json=body)
    assert response.status_code == 401, f"{method.upper()} {url} returned {response.status_code}"


async def test_ledger_list_returns_envelope(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/quality/deviation/ledger", params={"page": 1, "page_size": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert set(payload["data"]) >= {"items", "total", "page", "page_size"}
    assert isinstance(payload["data"]["items"], list)
    assert payload["meta"]["page"] == 1


async def test_ledger_statistics_shape(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/quality/deviation/ledger/statistics")
    assert response.status_code == 200
    data = response.json()["data"]
    for key in ("total", "pending", "returned", "closed", "department_distribution", "status_distribution"):
        assert key in data


async def test_ledger_detail_not_found(auth_client: AsyncClient) -> None:
    response = await auth_client.get(f"/api/v1/quality/deviation/ledger/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_ledger_status_options(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/quality/deviation/ledger/status-options")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    values = {item["value"] for item in items}
    assert {"pending_investigation", "returned", "closed"} <= values


async def test_ledger_create_requires_fields(auth_client: AsyncClient) -> None:
    response = await auth_client.post("/api/v1/quality/deviation/ledger", json={})
    assert response.status_code == 422
