# mypy: ignore-errors
from __future__ import annotations

import uuid

import pytest

from app.modules.hr.schemas import DepartmentCreate
from app.modules.hr.service import DepartmentService


@pytest.fixture
def dept_data():
    return DepartmentCreate(
        name="研发部",
        code=f"DEPT-{uuid.uuid4().hex[:6]}",
    )


async def test_create_department(db_session, dept_data):
    svc = DepartmentService(session=db_session)
    dept = await svc.create_department(dept_data)
    assert dept.name == "研发部"


async def test_get_department(db_session, dept_data):
    svc = DepartmentService(session=db_session)
    dept = await svc.create_department(dept_data)
    fetched = await svc.get_department(dept.id)
    assert fetched.name == "研发部"


async def test_delete_department(db_session, dept_data):
    from app.core.exceptions import NotFoundException

    svc = DepartmentService(session=db_session)
    dept = await svc.create_department(dept_data)
    await svc.delete_department(dept.id)
    with pytest.raises(NotFoundException):
        await svc.get_department(dept.id)
