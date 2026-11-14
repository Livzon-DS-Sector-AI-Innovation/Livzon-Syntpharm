# mypy: ignore-errors
"""HR module test fixtures."""

from __future__ import annotations

import uuid
from datetime import date

import pytest


@pytest.fixture
def sample_employee_data():
    uid = uuid.uuid4().hex[:8]
    return {
        "employee_number": f"EMP-{uid}",
        "name": "张三",
        "department": "生产部",
        "position": "工艺工程师",
        "hire_date": date(2024, 3, 15),
        "status_category": "在职",
    }
