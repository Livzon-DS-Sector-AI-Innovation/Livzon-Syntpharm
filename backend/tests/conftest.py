# mypy: ignore-errors
"""Root test configuration — auth fixtures and shared DB session.

Provides three client fixtures:
- auth_client: authenticated as a normal user
- admin_client: authenticated with a named admin user
- anonymous_client: no authentication

Phase 1 authentication: ``current_user`` may be None.
Permission enforcement is not yet implemented.
Fixtures override ``get_db`` and ``get_current_user`` only.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.platform.identity.deps import get_current_user
from app.platform.identity.models import User

# ── Helpers ──────────────────────────────────────────────────────────


def _make_user(
    name: str,
    employee_no: str,
    *,
    feishu_open_id: str | None = None,
) -> User:
    return User(
        name=name,
        employee_no=employee_no,
        feishu_open_id=feishu_open_id,
    )


def _build_client(
    session: AsyncSession,
    user: User | None,
) -> tuple:
    """Wire up dependency overrides and return ``(AsyncClient ctx, cleanup)``."""

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        try:
            yield session
        finally:
            pass

    async def _override_get_current_user() -> User | None:
        return user

    from app.main import app  # lazy — only imported when API tests request auth clients

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


@pytest.fixture(scope="session")
def _test_engine():
    """Session-scoped test database engine — created once, reused across tests."""
    from app.core.config import get_settings

    return create_async_engine(
        get_settings().DATABASE_URL,
        poolclass=pool.NullPool,
    )


@pytest.fixture
async def db_session(_test_engine) -> AsyncIterator[AsyncSession]:
    """Provide an AsyncSession with savepoint isolation.

    Uses an outer connection-level transaction.  When application code
    calls ``session.commit()`` (e.g. inside API endpoints), only a
    savepoint is committed.  The outer transaction is always rolled
    back at teardown, so no test can leak data to another test.
    """
    async with _test_engine.connect() as connection:
        async with connection.begin():
            factory = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            async with factory() as session:
                yield session
                await session.rollback()


@pytest.fixture
async def auth_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Authenticated client with a unique test user per test.

    Overrides ``get_db`` to use the test session and ``get_current_user``
    to return the test user.  Phase 1 auth does not enforce permissions,
    so no permission bypass override is needed.
    """
    test_user = _make_user(
        "Test User",
        f"TEST-{uuid.uuid4().hex[:8]}",
        feishu_open_id=f"test_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(test_user)
    await db_session.flush()

    client, cleanup = _build_client(db_session, test_user)
    async with client:
        yield client
    cleanup()


@pytest.fixture
async def admin_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Authenticated client with a unique admin test user per test.

    Identical to ``auth_client`` in Phase 1 — Phase 2 will add admin
    permission overrides when RBAC is implemented.
    """
    test_user = _make_user(
        "Admin User",
        f"ADMIN-{uuid.uuid4().hex[:8]}",
        feishu_open_id=f"admin_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(test_user)
    await db_session.flush()

    client, cleanup = _build_client(db_session, test_user)
    async with client:
        yield client
    cleanup()


@pytest.fixture
async def anonymous_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Unauthenticated client — ``get_current_user`` returns ``None``.

    Protected endpoints will return 401.
    Public endpoints will return 200.
    """
    client, cleanup = _build_client(db_session, None)
    async with client:
        yield client
    cleanup()


# Backward-compatibility alias
@pytest.fixture
async def client(auth_client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """Alias for ``auth_client`` (backward compatibility)."""
    yield auth_client
