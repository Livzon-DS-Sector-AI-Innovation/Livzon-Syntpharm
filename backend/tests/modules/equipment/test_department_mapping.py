"""Tests for department mapping logic in equipment import."""

from unittest.mock import MagicMock

import pytest


class MockDB:
    def __init__(self):
        self.executed_sql = []

    async def execute(self, stmt):
        self.executed_sql.append(str(stmt))
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
    from app.modules.equipment.api.batch_import import map_department_name_v3

    db = MockDB()
    name, id_val = await map_department_name_v3("检验室", db)
    assert name == "质量控制部"
    assert id_val == "uuid-quality-control"


@pytest.mark.asyncio
async def test_solvent_workshop_mapping():
    from app.modules.equipment.api.batch_import import map_department_name_v3

    db = MockDB()
    name, id_val = await map_department_name_v3("溶剂回收车间-401岗", db)
    assert name == "溶剂回收车间"
    assert id_val == "uuid-solvent-recovery"


@pytest.mark.asyncio
async def test_unknown_department_returns_none():
    from app.modules.equipment.api.batch_import import map_department_name_v3

    db = MockDB()
    name, id_val = await map_department_name_v3("不存在的火星部门", db)
    assert name is None
    assert id_val is None
