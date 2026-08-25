import pytest
from app.modules.equipment.schemas.equipment import EquipmentImportRow

def test_equipment_import_row_all_fields():
    """Test EquipmentImportRow with all fields"""
    row = EquipmentImportRow(
        资产编号="TEST001",
        资产说明="测试设备",
        实物所在部门="质量控制部",
        资产类别说明="固定资产.房屋建筑物",
        当前成本=120000.0,
        报废状态="未报废",
        数量=2
    )
    assert row.资产编号 == "TEST001"
    assert row.资产说明 == "测试设备"
    assert row.实物所在部门 == "质量控制部"
    assert row.资产类别说明 == "固定资产.房屋建筑物"
    assert row.当前成本 == 120000.0
    assert row.报废状态 == "未报废"
    assert row.数量 == 2

def test_equipment_import_row_minimal_fields():
    """Test EquipmentImportRow with minimal fields"""
    row = EquipmentImportRow()
    assert row.资产编号 is None
    assert row.资产说明 is None
    assert row.实物所在部门 is None
    assert row.资产类别说明 is None
    assert row.当前成本 is None
    assert row.报废状态 is None
    assert row.数量 is None

def test_equipment_import_row_partial_fields():
    """Test EquipmentImportRow with partial fields"""
    row = EquipmentImportRow(
        资产编号="TEST002",
        当前成本="¥100,000"
    )
    assert row.资产编号 == "TEST002"
    assert row.当前成本 == "¥100,000"
    assert row.资产说明 is None

def test_equipment_import_row_numeric_types():
    """Test EquipmentImportRow accepts different numeric types"""
    row1 = EquipmentImportRow(当前成本=100.5)
    assert row1.当前成本 == 100.5
    
    row2 = EquipmentImportRow(当前成本="200.5")
    assert row2.当前成本 == "200.5"
    
    row3 = EquipmentImportRow(数量=5)
    assert row3.数量 == 5
    
    row4 = EquipmentImportRow(数量=5.5)
    assert row4.数量 == 5.5
