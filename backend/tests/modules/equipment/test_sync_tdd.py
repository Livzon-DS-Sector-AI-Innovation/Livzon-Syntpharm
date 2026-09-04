from io import BytesIO

import pandas as pd
import pytest
from sqlalchemy import select

from app.modules.equipment.models.equipment import Equipment, EquipmentSyncLog
from app.modules.equipment.service.equipment import sync_equipments_with_audit
from app.modules.hr.models import HrDepartment


def _create_excel(rows) -> bytes:
    """辅助函数：将字典列表转换为 Excel 二进制流 (匹配 EXCEL_HEADER_ROW = 4)"""
    cols = [
        "资产编号",
        "设备名称",
        "实物所在部门",
        "实物所在地点",
        "当前成本",
        "帐面净值",
        "型号",
        "制造商",
        "启用日期",
    ]
    # 前 4 行写占位数据（非空），确保 pandas 不会跳过
    preamble = pd.DataFrame([["placeholder"] * len(cols) for _ in range(4)], columns=cols)
    data = pd.DataFrame(rows, columns=cols)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        preamble.to_excel(writer, index=False, header=False, startrow=0)
        data.to_excel(writer, index=False, header=True, startrow=4)
    output.seek(0)
    return output.read()


@pytest.mark.asyncio
async def test_tb01_exact_match_updates_cost(db_session, seed_basic_data):
    """TB-01: 验证完全匹配时，成本和净值被正确更新"""
    dept = await db_session.execute(select(HrDepartment).where(HrDepartment.name == "201车间"))
    d = dept.scalar_one()
    equip = Equipment(
        asset_no="T001", name="OldName", department_id=d.id, current_cost=100.0, book_value=50.0, is_deleted=False
    )
    db_session.add(equip)
    await db_session.commit()

    excel_data = _create_excel(
        [
            {
                "资产编号": "T001",
                "设备名称": "NewName",
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

    result = await sync_equipments_with_audit(db_session, excel_data, file_name="test.xlsx")

    assert result.updated == 1
    updated = await db_session.get(Equipment, equip.id)
    assert updated.current_cost == 200.0
    assert updated.book_value == 100.0
    assert updated.name == "NewName"


@pytest.mark.asyncio
async def test_tb02_soft_delete_missing_assets(db_session, seed_basic_data):
    """TB-02: 验证 Excel 中消失的设备被软删除"""
    dept = await db_session.execute(select(HrDepartment).where(HrDepartment.name == "201车间"))
    d = dept.scalar_one()
    equip = Equipment(asset_no="DEL001", name="ToBeDeleted", department_id=d.id, is_deleted=False)
    db_session.add(equip)
    await db_session.commit()

    excel_data = _create_excel([])
    result = await sync_equipments_with_audit(db_session, excel_data, file_name="empty.xlsx")

    assert result.deleted == 1
    deleted = await db_session.get(Equipment, equip.id)
    assert deleted.is_deleted


@pytest.mark.asyncio
async def test_tb04_threshold_fuse(db_session, seed_basic_data):
    """TB-04: 验证缺失比例超过 5% 时触发熔断"""
    dept = await db_session.execute(select(HrDepartment).where(HrDepartment.name == "201车间"))
    d = dept.scalar_one()
    for i in range(20):
        db_session.add(Equipment(asset_no=f"F{i}", name=f"E{i}", department_id=d.id, is_deleted=False))
    await db_session.commit()

    excel_data = _create_excel(
        [
            {
                "资产编号": "F0",
                "设备名称": "One",
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

    with pytest.raises(ValueError, match="安全熔断"):
        await sync_equipments_with_audit(db_session, excel_data, file_name="fuse.xlsx")


@pytest.mark.asyncio
async def test_tb04_audit_log_created(db_session, seed_basic_data):
    """TB-04: 验证同步后生成了审计日志"""
    await db_session.execute(select(HrDepartment).where(HrDepartment.name == "201车间"))
    excel_data = _create_excel(
        [
            {
                "资产编号": "LOG01",
                "设备名称": "LogTest",
                "实物所在部门": "201车间",
                "实物所在地点": "-",
                "当前成本": 10,
                "帐面净值": 5,
                "型号": "",
                "制造商": "",
                "启用日期": None,
            }
        ]
    )

    await sync_equipments_with_audit(db_session, excel_data, operator_id=None, file_name="audit_test.xlsx")

    logs = await db_session.execute(select(EquipmentSyncLog))
    log = logs.scalars().first()
    assert log is not None
    assert log.file_name == "audit_test.xlsx"
    assert log.summary["inserted"] == 1
