from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.database import get_db
from app.main import app
from app.platform.identity import deps


def make_request(authorization: str | None = None) -> Request:
    headers = []
    if authorization:
        headers.append((b"authorization", authorization.encode("utf-8")))
    return Request({"type": "http", "headers": headers})


@pytest.mark.anyio
async def test_current_user_defaults_to_system_admin_without_token(monkeypatch) -> None:
    default_admin = SimpleNamespace(id="admin-id", name="系统管理员", role="admin")

    async def fake_get_or_create_system_admin(db):
        return default_admin

    monkeypatch.setattr(
        deps, "get_or_create_system_admin", fake_get_or_create_system_admin
    )

    user = await deps.get_current_user(
        make_request(),
        db=object(),
        settings=SimpleNamespace(SECRET_KEY="test-secret"),
        auth_token=None,
    )

    assert user is default_admin


@pytest.mark.anyio
async def test_me_endpoint_returns_system_admin_without_token(monkeypatch) -> None:
    default_admin = SimpleNamespace(
        id=uuid4(),
        name="系统管理员",
        username="system_admin",
        role="admin",
        status="active",
        auth_source="local",
    )

    async def fake_get_db():
        yield object()

    async def fake_get_or_create_system_admin(db):
        return default_admin

    monkeypatch.setattr(
        deps, "get_or_create_system_admin", fake_get_or_create_system_admin
    )
    app.dependency_overrides[get_db] = fake_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/identity/me")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["username"] == "system_admin"
    assert payload["data"]["name"] == "系统管理员"
    assert payload["data"]["role"] == "admin"


@pytest.mark.anyio
async def test_current_user_defaults_to_system_admin_for_invalid_token(monkeypatch) -> None:
    default_admin = SimpleNamespace(id="admin-id", name="系统管理员", role="admin")

    async def fake_get_or_create_system_admin(db):
        return default_admin

    monkeypatch.setattr(
        deps, "get_or_create_system_admin", fake_get_or_create_system_admin
    )

    user = await deps.get_current_user(
        make_request("Bearer not-a-valid-jwt"),
        db=object(),
        settings=SimpleNamespace(SECRET_KEY="test-secret"),
        auth_token=None,
    )

    assert user is default_admin
