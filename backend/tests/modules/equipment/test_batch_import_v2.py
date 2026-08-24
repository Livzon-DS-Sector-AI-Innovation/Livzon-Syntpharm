"""设备导入 v2 功能测试 (TDD)."""

import pytest

from app.core.database import async_session_factory
from app.modules.equipment.api.batch_import import DEPT_MAPPING_V3, map_department_name_v3


def test_dept_mapping_v2_coverage() -> None:
    """测试映射表是否包含关键别名"""
    assert "检验室" in DEPT_MAPPING_V3
    assert DEPT_MAPPING_V3["检验室"] == "质量控制部"
    assert "头孢合成一车间" in DEPT_MAPPING_V3
    assert DEPT_MAPPING_V3["头孢合成一车间"] == "201车间"


@pytest.mark.asyncio
async def test_map_department_strict_alias() -> None:
    """测试别名映射逻辑"""
    async with async_session_factory() as db:
        name, dept_id = await map_department_name_v3("检验室", db)
        assert name == "质量控制部"
        assert dept_id is not None


@pytest.mark.asyncio
async def test_map_department_strict_workshop() -> None:
    """测试车间编号映射"""
    async with async_session_factory() as db:
        name, dept_id = await map_department_name_v3("头孢合成一车间", db)
        assert name == "201车间"
        assert dept_id is not None


@pytest.mark.asyncio
async def test_map_department_strict_special_format() -> None:
    """测试溶剂回收车间特殊格式归口"""
    async with async_session_factory() as db:
        name, dept_id = await map_department_name_v3("溶剂回收车间-404岗", db)
        assert name == "溶剂回收车间"
        assert dept_id is not None


@pytest.mark.asyncio
async def test_map_department_strict_nonexistent() -> None:
    """测试不存在的部门返回 None"""
    async with async_session_factory() as db:
        name, dept_id = await map_department_name_v3("银河系漫游指南部", db)
        assert dept_id is None
