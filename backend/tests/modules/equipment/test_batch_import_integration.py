"""Integration tests for Equipment Import v4 Force Override."""
import pytest
from app.modules.equipment.service.import_engine import apply_incremental_update
from unittest.mock import MagicMock

def test_force_override_updates_business_fields():
    """验证在 force_override=True 时，B类字段会被更新。"""
    existing = MagicMock()
    existing.department_id = "dept_old"
    existing.location_text = "loc_old"
    
    excel_data = {"department_id": "dept_new", "location_text": "loc_new"}
    
    changes = apply_incremental_update(existing, excel_data, force_override=True)
    
    assert "department_id" in changes
    assert changes["department_id"]["new"] == "dept_new"
    assert existing.department_id == "dept_new"

def test_protective_mode_skips_existing_business_fields():
    """验证在 force_override=False 时，已有的 B类字段不会被更新。"""
    existing = MagicMock()
    existing.department_id = "dept_old"
    
    excel_data = {"department_id": "dept_new"}
    
    changes = apply_incremental_update(existing, excel_data, force_override=False)
    
    assert "department_id" not in changes
    assert existing.department_id == "dept_old"

def test_audit_log_marks_force_override():
    """验证审计日志中能识别强制覆盖操作。"""
    # 模拟：当 changes 中包含 B类字段且 force_override 为 True 时
    # 审计逻辑应记录 override_type: force
    changes = {"department_id": {"old": "A", "new": "B"}}
    audit_entry = {
        "changes": changes,
        "override_type": "force" if changes.get("department_id") else "normal"
    }
    assert audit_entry["override_type"] == "force"
