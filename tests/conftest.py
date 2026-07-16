# mypy: ignore-errors
"""Root test configuration — auth fixtures and shared DB session.

Provides three client fixtures:
- auth_client: authenticated as a normal user (bypasses permission checks)
- admin_client: authenticated as an admin user (bypasses all checks)
- anonymous_client: no authentication (gets 401 for protected endpoints)

Production authentication logic is NOT weakened — we only override
FastAPI dependency injection during tests.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app  # noqa: F401  (trigger module registration)
from app.platform.identity.deps import get_current_user
from app.platform.identity.models import User  # noqa: F401

settings = get_settings()

# Test engine uses NullPool so each test gets a fresh connection on its own event loop.
_test_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=pool.NullPool,
)
_test_session_factory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _make_user(
    name: str,
    employee_no: str,
    *,
    feishu_open_id: str | None = None,
) -> User:
    """Create a transient User object (not persisted)."""
    return User(
        name=name,
        employee_no=employee_no,
        feishu_open_id=feishu_open_id,
    )


def _build_client(
    session: AsyncSession,
    user: User | None,
    *,
    is_admin: bool = False,
    bypass_permissions: bool = True,
) -> tuple:
    """Wire up dependency overrides and return ``(AsyncClient ctx, cleanup)``."""

    # DB override
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        try:
            yield session
        finally:
            pass

    # Auth overrides
    async def _override_get_current_user() -> User | None:
        return user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    def cleanup():
        app.dependency_overrides.clear()

    return client, cleanup


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide an AsyncSession that rolls back after each test."""
    async with _test_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def auth_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Authenticated client acting as a normal (non-admin) user.

    Permission checks (``require_permission``) are bypassed so that
    business-logic API tests can run without setting up real RBAC data.
    """
    test_user = _make_user(
        "Test User",
        "TEST-001",
        feishu_open_id="test_open_id",
    )
    db_session.add(test_user)
    await db_session.flush()

    client, cleanup = _build_client(db_session, test_user, bypass_permissions=True)
    async with client:
        yield client
    cleanup()
    await db_session.rollback()


@pytest.fixture
async def admin_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Authenticated client acting as an admin user.

    Passes ``require_user``, ``require_admin``, and ``require_permission``
    checks — use this for endpoints that demand administrator privileges.
    """
    test_user = _make_user(
        "Admin User",
        "ADMIN-001",
        feishu_open_id="admin_open_id",
    )
    db_session.add(test_user)
    await db_session.flush()

    client, cleanup = _build_client(
        db_session,
        test_user,
        is_admin=True,
        bypass_permissions=True,
    )
    async with client:
        yield client
    cleanup()
    await db_session.rollback()


@pytest.fixture
async def anonymous_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Unauthenticated client — ``get_current_user`` returns ``None``.

    Protected endpoints (those using ``require_user`` or ``require_admin``)
    will return 401.  Use this to verify that public endpoints work without
    login and that protected endpoints correctly reject anonymous access.
    """
    client, cleanup = _build_client(db_session, None, bypass_permissions=False)
    async with client:
        yield client
    cleanup()
    await db_session.rollback()


# Backward-compatibility alias — existing tests that use ``client`` will
# keep working.  New tests should prefer ``auth_client`` / ``admin_client``
# / ``anonymous_client`` for clarity.
@pytest.fixture
async def client(auth_client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """Alias for ``auth_client`` (backward compatibility)."""
    yield auth_client
