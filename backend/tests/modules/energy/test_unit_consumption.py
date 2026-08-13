"""Unit consumption target tests"""

import pytest

from app.modules.energy.service import (
    calculate_deviation_rate,
    calculate_unit_consumption,
    construct_ai_prompt,
    determine_deviation_status,
)


class TestUnitConsumptionCalculation:
    """测试单耗计算"""

    @pytest.mark.asyncio
    async def test_normal_calculation(self) -> None:
        """正常计算"""
        result = await calculate_unit_consumption(30000.0, 12000)
        assert result == 2.5

    @pytest.mark.asyncio
    async def test_precision(self) -> None:
        """精度测试"""
        result = await calculate_unit_consumption(10000.0, 3333)
        assert result == 3.0003  # 10000/3333 = 3.00030003...

    @pytest.mark.asyncio
    async def test_zero_production_raises_error(self) -> None:
        """产量为0应抛出异常"""
        with pytest.raises(ValueError, match="产量必须为正整数"):
            await calculate_unit_consumption(1000.0, 0)

    @pytest.mark.asyncio
    async def test_negative_production_raises_error(self) -> None:
        """负数产量应抛出异常"""
        with pytest.raises(ValueError, match="产量必须为正整数"):
            await calculate_unit_consumption(1000.0, -100)

    @pytest.mark.asyncio
    async def test_single_unit_production(self) -> None:
        """产量为1的边界情况"""
        result = await calculate_unit_consumption(500.0, 1)
        assert result == 500.0


class TestDeviationRateCalculation:
    """测试偏差率计算"""

    @pytest.mark.asyncio
    async def test_positive_deviation(self) -> None:
        """正偏差（超标）"""
        result = calculate_deviation_rate(2.5, 2.3)
        assert result == 8.7

    @pytest.mark.asyncio
    async def test_negative_deviation(self) -> None:
        """负偏差（优于目标）"""
        result = calculate_deviation_rate(2.1, 2.3)
        assert result == -8.7

    @pytest.mark.asyncio
    async def test_zero_deviation(self) -> None:
        """无偏差"""
        result = calculate_deviation_rate(2.3, 2.3)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_large_deviation(self) -> None:
        """大偏差"""
        result = calculate_deviation_rate(3.0, 2.0)
        assert result == 50.0

    @pytest.mark.asyncio
    async def test_zero_target_raises_error(self) -> None:
        """目标值为0应抛出异常"""
        with pytest.raises(ValueError, match="目标值必须为正数"):
            calculate_deviation_rate(2.5, 0)


class TestDeviationStatus:
    """测试偏差状态判定"""

    @pytest.mark.asyncio
    async def test_normal_status(self) -> None:
        """偏差 ≤ 5% 为 normal"""
        assert determine_deviation_status(5.0) == "normal"
        assert determine_deviation_status(-5.0) == "normal"
        assert determine_deviation_status(0.0) == "normal"
        assert determine_deviation_status(3.5) == "normal"

    @pytest.mark.asyncio
    async def test_warning_status(self) -> None:
        """5% < 偏差 ≤ 15% 为 warning"""
        assert determine_deviation_status(5.01) == "warning"
        assert determine_deviation_status(15.0) == "warning"
        assert determine_deviation_status(-10.0) == "warning"

    @pytest.mark.asyncio
    async def test_critical_status(self) -> None:
        """偏差 > 15% 为 critical"""
        assert determine_deviation_status(15.01) == "critical"
        assert determine_deviation_status(30.0) == "critical"
        assert determine_deviation_status(-20.0) == "critical"

    @pytest.mark.asyncio
    async def test_unknown_status(self) -> None:
        """None 返回 unknown"""
        assert determine_deviation_status(None) == "unknown"


class TestAIPromptConstruction:
    """测试 AI Prompt 构造"""

    @pytest.mark.asyncio
    async def test_prompt_with_target(self) -> None:
        """有目标值时的 Prompt"""
        analysis_data = {
            "workshop_name": "装配车间A",
            "analysis_month": "2026-08",
            "total_energy_kwh": 30000.0,
            "manual_production": 12000,
            "converted_production": 12000.0,
            "production_details": [
                {"name": "测试产品A", "quantity": 10000, "factor": 1.0, "converted_qty": 10000},
                {"name": "测试产品B", "quantity": 2500, "factor": 0.8, "converted_qty": 2000},
            ],
            "actual_unit_consumption": 2.5,
            "target_unit_consumption": 2.3,
            "deviation_rate": 8.7,
            "deviation_status": "warning",
        }

        prompt = construct_ai_prompt(analysis_data)

        assert "装配车间A" in prompt
        assert "2026-08" in prompt
        assert "30000.00" in prompt
        assert "12000" in prompt
        assert "2.5000" in prompt
        assert "2.3000" in prompt
        assert "+8.70%" in prompt
        assert "warning" in prompt
        assert "分析可能导致偏差的原因" in prompt

    @pytest.mark.asyncio
    async def test_prompt_without_target(self) -> None:
        """无目标值时的 Prompt"""
        analysis_data = {
            "workshop_name": "装配车间A",
            "analysis_month": "2026-08",
            "total_energy_kwh": 30000.0,
            "manual_production": 12000,
            "converted_production": 12000.0,
            "production_details": [
                {"name": "测试产品A", "quantity": 10000, "factor": 1.0, "converted_qty": 10000},
                {"name": "测试产品B", "quantity": 2500, "factor": 0.8, "converted_qty": 2000},
            ],
            "actual_unit_consumption": 2.5,
            "target_unit_consumption": None,
            "deviation_rate": None,
            "deviation_status": "unknown",
        }

        prompt = construct_ai_prompt(analysis_data)

        assert "未设定" in prompt
        assert "无法进行（缺少目标值）" in prompt
        assert "解释为什么需要设定目标" in prompt

    @pytest.mark.asyncio
    async def test_prompt_json_format_requirement(self) -> None:
        """Prompt 应要求 JSON 格式输出"""
        analysis_data = {
            "converted_production": 12000.0,
            "production_details": [{"name": "Test", "quantity": 100, "factor": 1.0, "converted_qty": 100}],
            "workshop_name": "Test",
            "analysis_month": "2026-08",
            "total_energy_kwh": 1000.0,
            "manual_production": 500,
            "actual_unit_consumption": 2.0,
            "target_unit_consumption": 2.0,
            "deviation_rate": 0.0,
            "deviation_status": "normal",
        }

        prompt = construct_ai_prompt(analysis_data)

        assert "JSON" in prompt
        assert "summary" in prompt
        assert "detailed_analysis" in prompt
        assert "recommendations" in prompt
        assert "confidence_level" in prompt
