from io import BytesIO

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.equipment.models.equipment import Equipment
from app.modules.equipment.service.equipment import sync_equipments_with_audit
from app.modules.hr.models import HrDepartment


# 模拟 Excel 内容
def create_mock_excel(rows):
    df = pd.DataFrame(
        rows,
        columns=[
            "资产编号",
            "设备名称",
            "实物所在部门",
            "实物所在地点",
            "当前成本",
            "帐面净值",
            "型号",
            "制造商",
            "启用日期",
        ],
    )
    output = BytesIO()
    # 简单模拟 header=4 的情况，实际测试可能需要更复杂的 openpyxl 构造
    # 这里为了演示 TDD 流程，我们假设 Service 层能解析这个简单的流
    df.to_excel(output, index=False, header=True)
    output.seek(0)
    return output.read()


@pytest.mark.asyncio
async def test_sync_updates_cost_and_value(db: AsyncSession, seed_departments_and_locations):
    """测试：同步功能是否正确更新了成本和净值"""
    # Arrange: 准备一台已存在的设备
    dept = await db.execute(select(HrDepartment).where(HrDepartment.name == "201车间"))
    d = dept.scalar_one()

    equip = Equipment(
        asset_no="TEST001", name="旧设备", department_id=d.id, current_cost=100.0, book_value=50.0, is_deleted=False
    )
    db.add(equip)
    await db.commit()

    # Act: 执行同步（Excel 中成本变为 200）
    excel_data = create_mock_excel(
        [
            {
                "资产编号": "TEST001",
                "设备名称": "新设备",
                "实物所在部门": "201车间",
                "实物所在地点": "-",
                "当前成本": 200.0,
                "帐面净值": 100.0,
                "型号": "",
                "制造商": "",
                "启用日期": None,
            }
        ]
    )

    result = await sync_equipments_with_audit(db, excel_data, file_name="test.xlsx")

    # Assert
    assert result.updated == 1
    updated_equip = await db.get(Equipment, equip.id)
    assert updated_equip.current_cost == 200.0
    assert updated_equip.book_value == 100.0


@pytest.mark.asyncio
async def test_sync_soft_deletes_missing_assets(db: AsyncSession, seed_departments_and_locations):
    """测试：Excel 中消失的设备是否被软删除"""
    # Arrange
    dept = await db.execute(select(HrDepartment).where(HrDepartment.name == "201车间"))
    d = dept.scalar_one()
    equip = Equipment(asset_no="TO_DELETE", name="待删设备", department_id=d.id, is_deleted=False)
    db.add(equip)
    await db.commit()

    # Act: 上传一个空的 Excel
    excel_data = create_mock_excel([])
    result = await sync_equipments_with_audit(db, excel_data, file_name="empty.xlsx")

    # Assert
    assert result.deleted == 1
    deleted_equip = await db.get(Equipment, equip.id)
    assert deleted_equip.is_deleted


@pytest.mark.asyncio
async def test_sync_threshold_fuse(db: AsyncSession, seed_departments_and_locations):
    """测试：缺失比例超过 5% 时是否触发熔断"""
    # Arrange: 插入 100 台设备
    dept = await db.execute(select(HrDepartment).where(HrDepartment.name == "201车间"))
    d = dept.scalar_one()
    for i in range(100):
        db.add(Equipment(asset_no=f"FUSE{i}", name=f"设备{i}", department_id=d.id, is_deleted=False))
    await db.commit()

    # Act: 上传只包含 1 台设备的 Excel (缺失 99%)
    excel_data = create_mock_excel(
        [
            {
                "资产编号": "FUSE0",
                "设备名称": "唯一",
                "实物所在部门": "201车间",
                "实物所在地点": "-",
                "当前成本": 0,
                "帐面净值": 0,
                "型号": "",
                "制造商": "",
                "启用日期": None,
            }
        ]
    )

    # Assert
    with pytest.raises(ValueError, match="安全熔断"):
        await sync_equipments_with_audit(db, excel_data, file_name="fuse_test.xlsx")
