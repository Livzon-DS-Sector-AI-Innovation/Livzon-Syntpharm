# mypy: ignore-errors
"""Safety module test fixtures."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import HrDepartment
from app.modules.safety.risk_grading import RISK_GRADING_DEPARTMENTS

# 组织目录里已被飞书移除的部门：组织树不展示，后端也不接受作为新值
REMOVED_DEPARTMENT_NAME = "已撤销车间"


@pytest.fixture(autouse=True)
async def seed_risk_grading_departments(db_session: AsyncSession):
    """风险分级台账的管控层级校验依赖 hr.departments。

    测试库默认没有部门数据；这里按需求文档的 28 个部门名种一份等价数据，
    另加一个 status_is_deleted=True 的负例（验证它既不进选项也不可提交）。
    """
    suffix = uuid.uuid4().hex[:8]
    db_session.add_all(
        [
            HrDepartment(name=name, code=f"RISK-{suffix}-{index:02d}")
            for index, name in enumerate(RISK_GRADING_DEPARTMENTS)
        ]
    )
    db_session.add(HrDepartment(name=REMOVED_DEPARTMENT_NAME, code=f"RISK-{suffix}-X", status_is_deleted=True))
    await db_session.flush()
    yield


@pytest.fixture
def sample_hazard_data():
    return {
        "hazard_no": "HAZ-2026-001",
        "title": "化学品泄漏风险",
        "description": "存储区域存在泄漏风险",
        "risk_level": 2,
        "location": "化学品仓库A",
        "status": "open",
    }
