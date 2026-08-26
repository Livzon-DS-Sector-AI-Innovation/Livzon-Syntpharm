"""Shared test fixtures for equipment module tests."""

from typing import Any, Protocol, runtime_checkable
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import HrDepartment
from app.platform.identity.models import User


@runtime_checkable
class MockDBProtocol(Protocol):
    """Protocol defining the minimal database interface for testing."""

    async def execute(self, stmt: Any) -> MagicMock: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


def _extract_param_values(stmt: Any) -> str:
    """Extract all parameter values from a SQLAlchemy statement as a string for matching."""
    try:
        compiled = stmt.compile(compile_kwargs={"literal_binds": True})
        return str(compiled)
    except Exception:
        return str(stmt)


class MockDB:
    """Mock database for testing."""

    def __init__(self, departments: dict[str, str] | None = None) -> None:
        self.executed_sql: list[str] = []
        self.departments = departments or {
            "质量控制部": "uuid-quality-control",
            "201车间": "uuid-201-workshop",
            "溶剂回收车间": "uuid-solvent",
        }

    async def execute(self, stmt: Any) -> MagicMock:
        self.executed_sql.append(str(stmt))
        mock_result = MagicMock()
        sql_str = _extract_param_values(stmt)

        # Find which department is being looked up
        found_id = None
        for dept_name, dept_id in self.departments.items():
            if dept_name in sql_str:
                found_id = dept_id
                break

        mock_result.scalar_one_or_none.return_value = found_id
        return mock_result

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


def create_mock_department(dept_id: str, name: str) -> MagicMock:
    """Create a mock HrDepartment object."""
    mock_dept = MagicMock(spec=HrDepartment)
    mock_dept.id = dept_id
    mock_dept.name = name
    return mock_dept


@pytest.fixture
async def test_assignee(db_session: AsyncSession) -> User:
    """Create a test user for work order assignment."""
    user = User(
        username="test_assignee",
        employee_no="EMP001",
        name="Test Assignee",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user
