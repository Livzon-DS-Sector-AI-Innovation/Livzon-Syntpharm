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


@pytest.fixture
async def org_scope_settings(db_session):
    """Seed the HR org-sync scope rows required by ``load_org_scope(required=True)``."""
    from app.core.config_model import ModuleSetting
    from tests.fixtures.org_scope import ROOT_ID, ROOT_NAME

    db_session.add_all(
        [
            ModuleSetting(module="hr", key="HR_ORG_SYNC_ROOT_DEPARTMENT_ID", value=ROOT_ID, value_type="string"),
            ModuleSetting(module="hr", key="HR_ORG_SYNC_ROOT_DEPARTMENT_NAME", value=ROOT_NAME, value_type="string"),
        ]
    )
    await db_session.flush()
    yield
