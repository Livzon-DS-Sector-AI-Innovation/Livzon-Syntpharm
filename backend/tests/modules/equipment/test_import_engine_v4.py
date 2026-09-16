"""设备批量导入 v4 核心逻辑测试."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.equipment.service.import_engine import (
    apply_incremental_update,
    find_existing_equipment,
)


class TestFindExistingEquipmentWarnings:
    """测试 find_existing_equipment 的结构化警告返回."""

    @pytest.mark.asyncio
    async def test_fuzzy_match_returns_warning(self):
        """测试模糊匹配成功时返回结构化警告."""
        # Mock db and existing equipment
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_equipment = MagicMock()
        mock_equipment.asset_no = "EXISTING_ASSET_001"
        mock_result.scalar_one_or_none.return_value = mock_equipment
        mock_db.execute.return_value = mock_result

        # Call the function with fuzzy match conditions (no asset_no)
        dept_id = uuid.uuid4()
        equipment, strategy, warnings = await find_existing_equipment(
            db=mock_db,
            asset_no=None,  # Trigger fuzzy match
            equipment_tag=None,
            name="Test Equipment",
            department_id=dept_id,
            location_text="Location A",
        )

        assert strategy == "fuzzy"
        assert equipment is not None
        assert len(warnings) > 0
        # Check structured warning
        warning = warnings[0]
        assert warning.field == "asset_no"
        assert warning.level == "WARN"
        assert "EXISTING_ASSET_001" in warning.message


class TestIncrementalUpdateProtection:
    """测试增量更新中的 B 类字段保护逻辑."""

    def test_b_field_protected_on_mapping_failure(self):
        """测试当映射失败（new_val 为 None）时，B 类字段保留原值."""
        existing = MagicMock()
        existing.department_id = uuid.uuid4()
        existing.current_cost = 1000.0

        excel_data = {
            "current_cost": 2000.0,  # A类：应更新
            "department_id": None,  # B类：映射失败，应保护
        }

        changes = apply_incremental_update(existing, excel_data, force_override=False)

        # A类字段应更新
        assert existing.current_cost == 2000.0
        assert "current_cost" in changes

        # B类字段应保持原值（因为 new_val 是 None）
        # 注意：目前的实现中，如果 new_val 是 None，setattr 不会执行
        # 我们需要验证这一点
        assert existing.department_id is not None

    def test_b_field_updated_on_success(self):
        """测试当映射成功时，B 类字段正常更新."""
        existing = MagicMock()
        existing.department_id = None
        new_dept_id = uuid.uuid4()

        excel_data = {"department_id": new_dept_id}

        changes = apply_incremental_update(existing, excel_data, force_override=False)

        assert existing.department_id == new_dept_id
        assert "department_id" in changes
