"""设备批量导入功能测试."""

from difflib import SequenceMatcher

import pytest

from app.modules.equipment.api.batch_import import (
    fuzzy_match_department,
    get_column_value,
)


class TestFuzzyMatchDepartment:
    """测试部门名称模糊匹配功能."""

    def test_exact_match(self) -> None:
        """测试精确匹配."""
        departments = ["设备工程部", "动力部", "201车间"]
        result = fuzzy_match_department("设备工程部", departments, threshold=0.8)
        assert result == "设备工程部"

    def test_fuzzy_match_high_similarity(self) -> None:
        """测试高相似度模糊匹配."""
        departments = ["设备工程部", "动力部", "201车间"]
        # "设备工程不" 与 "设备工程部" 相似度约 0.89
        result = fuzzy_match_department("设备工程不", departments, threshold=0.8)
        assert result == "设备工程部"

    def test_fuzzy_match_medium_similarity(self) -> None:
        """测试中等相似度模糊匹配."""
        departments = ["201车间", "202车间", "301车间"]
        # "201车问" 与 "201车间" 相似度约 0.86
        result = fuzzy_match_department("201车问", departments, threshold=0.8)
        assert result == "201车间"

    def test_no_match_below_threshold(self) -> None:
        """测试低于阈值的匹配应返回 None."""
        departments = ["质量控制部", "质量保证部"]
        # "质控部" 与任何部门相似度都 < 0.8
        result = fuzzy_match_department("质控部", departments, threshold=0.8)
        assert result is None

    def test_empty_input(self) -> None:
        """测试空输入."""
        departments = ["设备工程部"]
        result = fuzzy_match_department("", departments, threshold=0.8)
        assert result is None

    def test_empty_departments(self) -> None:
        """测试空部门列表."""
        result = fuzzy_match_department("设备工程部", [], threshold=0.8)
        assert result is None

    def test_best_match_selection(self) -> None:
        """测试选择最佳匹配."""
        departments = ["设备工程部", "设备管理科", "动力部"]
        # "设备工程" 应该匹配到 "设备工程部"（相似度更高）
        result = fuzzy_match_department("设备工程", departments, threshold=0.8)
        assert result == "设备工程部"

    def test_custom_threshold(self) -> None:
        """测试自定义阈值."""
        departments = ["质量控制部"]
        # 使用更低的阈值
        result = fuzzy_match_department("质控部", departments, threshold=0.7)
        # 相似度约 0.75，应该匹配
        assert result == "质量控制部"


class TestGetColumnValue:
    """测试列值获取功能."""

    def test_exact_column_name(self) -> None:
        """测试精确列名匹配."""
        row = {"资产编号": "EQ001", "名称": "离心机"}
        result = get_column_value(row, "资产编号")
        assert result == "EQ001"

    def test_alternative_column_name(self) -> None:
        """测试备选列名匹配."""
        row = {"编号": "EQ001", "Name": "离心机"}
        result = get_column_value(row, "资产编号")
        assert result == "EQ001"

    def test_column_not_found(self) -> None:
        """测试列名不存在."""
        row = {"其他字段": "value"}
        result = get_column_value(row, "资产编号")
        assert result is None

    def test_none_value(self) -> None:
        """测试值为 None."""
        row = {"资产编号": None}
        result = get_column_value(row, "资产编号")
        assert result is None


class TestSequenceMatcher:
    """测试相似度计算逻辑."""

    @pytest.mark.parametrize(
        "str1,str2,expected_min,expected_max",
        [
            ("设备工程不", "设备工程部", 0.8, 1.0),  # similar strings
            ("质控部", "质量控制部", 0.0, 0.8),  # different strings
            ("设备工程部", "设备工程部", 1.0, 1.0),  # identical strings
        ],
    )
    def test_similarity_scores(self, str1: str, str2: str, expected_min: float, expected_max: float) -> None:
        """测试字符串相似度计算."""
        score = SequenceMatcher(None, str1, str2).ratio()
        assert expected_min <= score <= expected_max
