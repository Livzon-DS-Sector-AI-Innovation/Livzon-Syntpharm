"""设备导入 v3 功能测试 (TDD)."""
import pytest
from app.modules.equipment.api.batch_import import get_column_value, parse_excel_date

# Test Case 1: 智能列名匹配 (Spec 2.2)
def test_fuzzy_column_matching():
    """测试后端是否能识别带空格的列名"""
    row = {" 资产编号 ": "TEST001", "标签号": "LB001"}
    assert get_column_value(row, "资产编号") == "TEST001"

# Test Case 2: Excel 序列号日期解析 (Spec 2.2)
def test_excel_serial_date_parsing():
    """测试是否能将 46196 转换为 2026-06-23"""
    result = parse_excel_date(46196)
    assert str(result) == "2026-06-23"

# Test Case 3: 数量字段映射到 technical_params (Spec 2.1)
def test_quantity_to_tech_params():
    """模拟前端发送的包含 technical_params 的数据结构"""
    # 这里主要验证后端 schema 是否能接收该字段
    from app.modules.equipment.schemas import EquipmentCreate
    data = {
        "asset_no": "TEST002",
        "name": "测试设备",
        "technical_params": {"数量": 5}
    }
    # 如果这一行不报错，说明 Schema 对齐成功
    schema = EquipmentCreate(**data)
    assert schema.technical_params["数量"] == 5
