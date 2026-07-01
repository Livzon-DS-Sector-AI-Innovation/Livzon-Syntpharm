"""HR module model tests."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.modules.hr.models import Employee


@pytest.mark.asyncio
async def test_employee_model_creation(db_session, sample_employee_data):
    employee = Employee(**sample_employee_data)
    db_session.add(employee)
    await db_session.commit()

    result = await db_session.execute(
        select(Employee).where(Employee.id == employee.id)
    )
    fetched = result.scalar_one()
    assert fetched.employee_number == sample_employee_data["employee_number"]
    assert fetched.name == "张三"
    assert fetched.hire_date == date(2024, 3, 15)
