"""Equipment module test fixtures."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppException, ForbiddenException
from app.main import app
from app.modules.equipment.deps import EquipmentAccessContext
from app.platform.identity.deps import get_current_user
from app.platform.identity.models import User
from app.platform.permission.deps import require_admin, require_user

settings = get_settings()

_test_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=pool.NullPool,
)
_test_session_factory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# All permission codes — return from get_user_permissions to bypass checks.
_ALL_PERMISSION_CODES = {
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
    "permission:role:manage",
}


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
async def _equipment_session() -> AsyncIterator[AsyncSession]:
    """Shared session for equipment API tests with test users pre-created."""
    async with _test_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_reporter(_equipment_session: AsyncSession) -> User:
    """Create a test reporter user in the shared session."""
    user = User(name="测试报修人", employee_no=f"EMP-R-{uuid.uuid4().hex[:8]}")
    _equipment_session.add(user)
    await _equipment_session.flush()
    await _equipment_session.refresh(user)
    return user


@pytest.fixture
async def test_assignee(_equipment_session: AsyncSession) -> User:
    """Create a test assignee user in the shared session."""
    user = User(name="测试维修员", employee_no=f"EMP-A-{uuid.uuid4().hex[:8]}")
    _equipment_session.add(user)
    await _equipment_session.flush()
    await _equipment_session.refresh(user)
    return user


async def _mock_equipment_access(*codes: str):
    """Mock dependency that returns EquipmentAccessContext."""
    async def _dependency(
        user: User,
        db: AsyncSession,
    ) -> EquipmentAccessContext:
        return EquipmentAccessContext(
            user=user,
            data_scope="all",  # Full access for testing
            department_user_ids=[],
            visible_department_ids=[],
        )
    return _dependency


@pytest.fixture
async def auth_client(
    _equipment_session: AsyncSession,
    test_reporter: User,
) -> AsyncIterator[AsyncClient]:
    """Authenticated client for equipment API tests.

    Uses the shared equipment session and bypasses permission checks.
    """
    session = _equipment_session

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        try:
            yield session
        finally:
            pass

    async def _override_get_current_user() -> User:
        return test_reporter

    async def _override_require_user() -> User:
        return test_reporter

    async def _override_require_admin() -> User:
        raise ForbiddenException("仅管理员可操作")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_user] = _override_require_user
    app.dependency_overrides[require_admin] = _override_require_admin

    perm_mock = AsyncMock(return_value=_ALL_PERMISSION_CODES)
    patcher = patch("app.platform.permission.deps.get_user_permissions", perm_mock)
    patcher.start()
    
    # Mock the require_equipment_access to return our mock dependency
    access_patcher = patch(
        "app.modules.equipment.deps.require_equipment_access",
        _mock_equipment_access
    )
    access_patcher.start()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    access_patcher.stop()
    patcher.stop()
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_client(
    _equipment_session: AsyncSession,
    test_reporter: User,
) -> AsyncIterator[AsyncClient]:
    """Admin-authenticated client for equipment API tests."""
    session = _equipment_session

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        try:
            yield session
        finally:
            pass

    async def _override_get_current_user() -> User:
        return test_reporter

    async def _override_require_user() -> User:
        return test_reporter

    async def _override_require_admin() -> User:
        return test_reporter

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_user] = _override_require_user
    app.dependency_overrides[require_admin] = _override_require_admin

    perm_mock = AsyncMock(return_value=_ALL_PERMISSION_CODES)
    patcher = patch("app.platform.permission.deps.get_user_permissions", perm_mock)
    patcher.start()
    
    # Mock the require_equipment_access to return our mock dependency
    access_patcher = patch(
        "app.modules.equipment.deps.require_equipment_access",
        _mock_equipment_access
    )
    access_patcher.start()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    access_patcher.stop()
    patcher.stop()
    app.dependency_overrides.clear()


@pytest.fixture
async def anonymous_client(
    _equipment_session: AsyncSession,
) -> AsyncIterator[AsyncClient]:
    """Unauthenticated client for equipment API tests."""
    session = _equipment_session

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        try:
            yield session
        finally:
            pass

    async def _override_get_current_user() -> None:
        return None

    async def _override_require_user():
        raise AppException(status_code=401, message="未登录")

    async def _override_require_admin():
        raise AppException(status_code=401, message="未登录")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_user] = _override_require_user
    app.dependency_overrides[require_admin] = _override_require_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# Backward-compatibility alias
@pytest.fixture
async def client(auth_client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """Alias for ``auth_client`` (backward compatibility)."""
    yield auth_client


@pytest.fixture
def mock_equipment_context(test_reporter: User) -> EquipmentAccessContext:
    """Create a mock EquipmentAccessContext for service tests."""
    return EquipmentAccessContext(
        user=test_reporter,
        data_scope="all",
        department_user_ids=[],
        visible_department_ids=[],
    )
