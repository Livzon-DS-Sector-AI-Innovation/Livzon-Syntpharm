"""Tests for smart inference logic in equipment import."""

from app.modules.equipment.api.batch_import import (
    infer_equipment_class,
    infer_importance,
    infer_status,
)


class TestInferEquipmentClass:
    def test_house_building_is_a(self):
        assert infer_equipment_class("固定资产.房屋建筑物") == "A"

    def test_transport_is_b(self):
        assert infer_equipment_class("固定资产.运输设备") == "B"

    def test_electronic_is_c(self):
        assert infer_equipment_class("固定资产.电子设备") == "C"

    def test_machine_is_c(self):
        assert infer_equipment_class("固定资产.机器设备") == "C"

    def test_default_is_c(self):
        assert infer_equipment_class(None) == "C"
        assert infer_equipment_class("其他未知类别") == "C"


class TestInferImportance:
    def test_high_cost_is_high(self):
        assert infer_importance(150000.0) == "高"

    def test_mid_cost_is_mid(self):
        assert infer_importance(75000.0) == "中"

    def test_low_cost_is_low(self):
        assert infer_importance(30000.0) == "低"

    def test_none_cost_is_mid(self):
        assert infer_importance(None) == "中"


class TestInferStatus:
    def test_not_scrapped_is_in_use(self):
        assert infer_status("未报废") == "在用"

    def test_scrapped_is_scrapped(self):
        assert infer_status("已报废") == "报废"

    def test_default_is_in_use(self):
        assert infer_status(None) == "在用"
        assert infer_status("") == "在用"
