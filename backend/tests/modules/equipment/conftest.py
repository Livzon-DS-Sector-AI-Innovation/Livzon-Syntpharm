# mypy: ignore-errors
"""Equipment module test fixtures."""

from __future__ import annotations

import uuid

import pytest

from app.modules.equipment.deps import EquipmentAccessContext
from app.platform.identity.models import User


@pytest.fixture
async def test_reporter(db_session) -> User:
    user = User(name="测试报修人", employee_no=f"EMP-R-{uuid.uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_assignee(db_session) -> User:
    user = User(name="测试维修员", employee_no=f"EMP-A-{uuid.uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
def mock_equipment_context(test_reporter: User) -> EquipmentAccessContext:
    return EquipmentAccessContext(
        user=test_reporter,
        data_scope="all",
        department_user_ids=[],
        visible_department_ids=[],
    )
