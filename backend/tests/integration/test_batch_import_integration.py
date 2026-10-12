"""Integration tests for Equipment Import v4 Force Override."""

from unittest.mock import MagicMock

from app.modules.equipment.service.import_engine import apply_incremental_update


def test_force_override_updates_business_fields():
    """验证在 force_override=True 时，B类字段会被更新。"""
    existing = MagicMock()
    existing.department_id = "dept_old"
    existing.location_text = "loc_old"

    excel_data = {"department_id": "dept_new", "location_text": "loc_new"}

    changes = apply_incremental_update(existing, excel_data, force_override=True)

    assert "department_id" in changes
    assert changes["department_id"]["new"] == "dept_new"  # type: ignore[index]
    assert existing.department_id == "dept_new"


def test_protective_mode_skips_existing_business_fields():
    """验证在 force_override=False 时，已有的 B类字段不会被更新。"""
    existing = MagicMock()
    existing.department_id = "dept_old"

    excel_data = {"department_id": "dept_new"}

    changes = apply_incremental_update(existing, excel_data, force_override=False)

    assert "department_id" not in changes
    assert existing.department_id == "dept_old"
