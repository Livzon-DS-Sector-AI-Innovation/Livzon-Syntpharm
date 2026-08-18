"""Tests for department mapping logic in equipment import."""

import pytest
from unittest.mock import AsyncMock, MagicMock

# 模拟异步数据库会话
class MockDB:
    def __init__(self):
        self.executed_sql = []
    
    async def execute(self, stmt):
        self.executed_sql.append(str(stmt))
        # 模拟查询结果：只有“质量控制部”和“溶剂回收车间”存在
        mock_result = MagicMock()
        if "质量控制部" in str(stmt):
            mock_result.scalar_one_or_none.return_value = "uuid-quality-control"
        elif "溶剂回收车间" in str(stmt):
            mock_result.scalar_one_or_none.return_value = "uuid-solvent-recovery"
        else:
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

@pytest.mark.asyncio
async def test_exact_match_in_mapping():
    """测试映射表中存在的部门"""
    from app.modules.equipment.api.batch_import import map_department_name_v3
    db = MockDB()
    name, id_val = await map_department_name_v3("检验室", db)
    assert name == "质量控制部"
    assert id_val == "uuid-quality-control"

@pytest.mark.asyncio
async def test_solvent_workshop_mapping():
    """测试溶剂回收车间各岗位的统一映射"""
    from app.modules.equipment.api.batch_import import map_department_name_v3
    db = MockDB()
    name, id_val = await map_department_name_v3("溶剂回收车间-401岗", db)
    assert name == "溶剂回收车间"
    assert id_val == "uuid-solvent-recovery"

@pytest.mark.asyncio
async def test_fallback_to_original_name():
    """测试映射表不存在但数据库中存在的部门（直接使用原名）"""
    from app.modules.equipment.api.batch_import import map_department_name_v3
    db = MockDB()
    # 假设系统中直接有一个叫“临时项目组”的部门
    name, id_val = await map_department_name_v3("临时项目组", db)
    assert name == "临时项目组"
    # 因为 MockDB 里没有这个部门的 ID，所以返回 None
    assert id_val is None

@pytest.mark.asyncio
async def test_unknown_department_returns_none():
    """测试完全未知的部门，应返回 None 但不报错"""
    from app.modules.equipment.api.batch_import import map_department_name_v3
    db = MockDB()
    name, id_val = await map_department_name_v3("不存在的火星部门", db)
    assert name is None
    assert id_val is None

@pytest.mark.asyncio
async def test_empty_input():
    """测试空输入"""
    from app.modules.equipment.api.batch_import import map_department_name_v3
    db = MockDB()
    name, id_val = await map_department_name_v3("", db)
    assert name is None
    assert id_val is None
