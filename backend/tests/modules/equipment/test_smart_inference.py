"""Tests for smart inference logic in equipment import."""

import pytest

from app.modules.equipment.api.batch_import import (
    infer_equipment_class,
    infer_importance,
    infer_status,
)


class TestInferEquipmentClass:
    @pytest.mark.parametrize(
        "category_description,expected",
        [
            ("固定资产.房屋建筑物", "A"),
            ("固定资产.运输设备", "B"),
            ("固定资产.电子设备", "C"),
            ("固定资产.机器设备", "C"),
            (None, "C"),
            ("其他未知类别", "C"),
        ],
    )
    def test_infer_equipment_class(self, category_description: str | None, expected: str) -> None:
        assert infer_equipment_class(category_description) == expected


class TestInferImportance:
    @pytest.mark.parametrize(
        "current_cost,expected",
        [
            (150000.0, "高"),
            (75000.0, "中"),
            (30000.0, "低"),
            (None, "中"),
        ],
    )
    def test_infer_importance(self, current_cost: float | None, expected: str) -> None:
        assert infer_importance(current_cost) == expected


class TestInferStatus:
    @pytest.mark.parametrize(
        "scrap_status,expected",
        [
            ("未报废", "在用"),
            ("已报废", "报废"),
            (None, "在用"),
            ("", "在用"),
        ],
    )
    def test_infer_status(self, scrap_status: str | None, expected: str) -> None:
        assert infer_status(scrap_status) == expected
