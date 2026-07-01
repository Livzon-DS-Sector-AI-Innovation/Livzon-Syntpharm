from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app  # noqa: A001
from app.platform.identity.models import User  # noqa: F401
from app.platform.identity.deps import get_current_user
from app.platform.permission.deps import require_user, require_permission, require_admin, get_user_permissions

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
async def client() -> AsyncIterator[AsyncClient]:
    """Provide an AsyncClient with authentication and permissions bypassed."""
    async with _test_session_factory() as session:
        # Create a test user
        test_user = User(
            name="Test User",
            employee_no="TEST-001",
            department="测试部",
            position="测试工程师",
            feishu_open_id="test_open_id",
        )
        session.add(test_user)
        await session.flush()

        async def _override_get_db() -> AsyncIterator[AsyncSession]:
            try:
                yield session
            finally:
                pass

        # Override all authentication dependencies
        async def _override_get_current_user() -> User:
            return test_user

        async def _override_require_user() -> User:
            return test_user

        async def _override_require_admin() -> User:
            return test_user

        # Override require_permission to bypass permission checks
        from app.platform.permission import deps as perm_deps
        original_require_permission = perm_deps.require_permission
        
        def _mock_require_permission(*codes):
            async def checker():
                return test_user
            return checker
        
        # Patch in the source module
        perm_deps.require_permission = _mock_require_permission
        
        # Also patch in all modules that import it
        import sys
        for module_name, module in sys.modules.items():
            if module and hasattr(module, 'require_permission'):
                if module.require_permission is original_require_permission:
                    module.require_permission = _mock_require_permission

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = _override_get_current_user
        app.dependency_overrides[require_user] = _override_require_user
        app.dependency_overrides[require_admin] = _override_require_admin
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
        
        # Restore original function
        perm_deps.require_permission = original_require_permission
        import sys
        for module_name, module in sys.modules.items():
            if module and hasattr(module, 'require_permission'):
                if module.require_permission is _mock_require_permission:
                    module.require_permission = original_require_permission
        app.dependency_overrides.clear()
        await session.rollback()
