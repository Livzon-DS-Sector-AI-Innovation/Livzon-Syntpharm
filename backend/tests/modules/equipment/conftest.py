"""Shared test fixtures for equipment module tests."""

import uuid
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.equipment.models.equipment import Location
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


@pytest.fixture
def project_root() -> Path:
    """Return the backend project root directory."""
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
async def seed_departments_and_locations(db_session: AsyncSession):
    """Seed basic departments and locations for equipment sync tests."""
    depts = [
        HrDepartment(name="201车间", code="DEPT-201", is_production=True),
        HrDepartment(name="质量控制部", code="DEPT-QC", is_production=False),
        HrDepartment(name="溶剂回收车间", code="DEPT-SOLVENT", is_production=True),
    ]
    for dept in depts:
        db_session.add(dept)

    uid = uuid.uuid4().hex[:6]
    locations = [
        Location(name="主厂房", code=f"LOC-MAIN-{uid}"),
        Location(name="仓库A", code=f"LOC-WH-A-{uid}"),
        Location(name="实验室", code=f"LOC-LAB-{uid}"),
    ]
    for loc in locations:
        db_session.add(loc)

    await db_session.flush()
    yield


@pytest.fixture
async def seed_basic_data(db_session: AsyncSession):
    """Seed basic data for equipment sync TDD tests (same as seed_departments_and_locations)."""
    depts = [
        HrDepartment(name="201车间", code="DEPT-201", is_production=True),
        HrDepartment(name="质量控制部", code="DEPT-QC", is_production=False),
        HrDepartment(name="溶剂回收车间", code="DEPT-SOLVENT", is_production=True),
    ]
    for dept in depts:
        db_session.add(dept)

    uid = uuid.uuid4().hex[:6]
    locations = [
        Location(name="主厂房", code=f"LOC-MAIN-{uid}"),
        Location(name="仓库A", code=f"LOC-WH-A-{uid}"),
        Location(name="实验室", code=f"LOC-LAB-{uid}"),
    ]
    for loc in locations:
        db_session.add(loc)

    await db_session.flush()
    yield
