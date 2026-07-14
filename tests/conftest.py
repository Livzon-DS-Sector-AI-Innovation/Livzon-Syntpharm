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
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppException, ForbiddenException
from app.main import app  # noqa: F401  (trigger module registration)
from app.platform.identity.deps import get_current_user
from app.platform.identity.models import User  # noqa: F401
from app.platform.permission.deps import require_admin, require_user

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

# All permission codes used in the app — extracted from source.
# Returning this set from get_user_permissions ensures all permission checks pass.
_ALL_PERMISSION_CODES = {
    "energy:alert:manage",
    "energy:alert:read",
    "energy:collect_log:read",
    "energy:device:manage",
    "energy:device:read",
    "energy:overview:read",
    "equipment:asset:create",
    "equipment:asset:delete",
    "equipment:asset:read",
    "equipment:asset:update",
    "equipment:inspection:create",
    "equipment:inspection:delete",
    "equipment:inspection:read",
    "equipment:inspection:update",
    "equipment:maintenance:create",
    "equipment:maintenance:delete",
    "equipment:maintenance:read",
    "equipment:maintenance:update",
    "equipment:personnel:manage",
    "equipment:personnel:read",
    "equipment:spare_part:create",
    "equipment:spare_part:read",
    "equipment:spare_part:update",
    "equipment:stats:read",
    "equipment:work_order:approve",
    "equipment:work_order:create",
    "equipment:work_order:read",
    "equipment:work_order:update",
    # Admin/super permissions
    "permission:role:manage",
}


# ── Helpers ──────────────────────────────────────────────────────────


def _make_user(
    name: str,
    employee_no: str,
    *,
    role: str = "member",
    feishu_open_id: str | None = None,
) -> User:
    """Create a transient User object (not persisted)."""
    return User(
        name=name,
        employee_no=employee_no,
        role=role,
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

    async def _override_require_user() -> User:
        if user is None:
            raise AppException(status_code=401, message="未登录")
        return user

    async def _override_require_admin() -> User:
        if user is None:
            raise AppException(status_code=401, message="未登录")
        if not is_admin:
            raise ForbiddenException("仅管理员可操作")
        return user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_user] = _override_require_user
    app.dependency_overrides[require_admin] = _override_require_admin

    # Patch get_user_permissions to return all permission codes.
    # This is called inside require_permission's checker at request time.
    # By returning all codes, we ensure all permission checks pass.
    perm_mock = AsyncMock(return_value=_ALL_PERMISSION_CODES)
    patcher = patch("app.platform.permission.deps.get_user_permissions", perm_mock)

    if bypass_permissions:
        patcher.start()

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    def cleanup():
        if bypass_permissions:
            patcher.stop()
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
        role="member",
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
        role="admin",
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
