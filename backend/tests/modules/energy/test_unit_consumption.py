"""Unit consumption target tests"""

from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.energy.service import (
    calculate_deviation_rate,
    calculate_unit_consumption,
    construct_ai_prompt,
    determine_deviation_status,
    prepare_ai_analysis_data,
)


class TestUnitConsumptionCalculation:
    """测试单耗计算"""

    async def test_normal_calculation(self) -> None:
        """正常计算"""
        result = await calculate_unit_consumption(30000.0, 12000)
        assert result == 2.5

    async def test_precision(self) -> None:
        """精度测试"""
        result = await calculate_unit_consumption(10000.0, 3333)
        assert result == 3.0003  # 10000/3333 = 3.00030003...

    async def test_fractional_production_not_truncated(self) -> None:
        """折算产量为小数时不得被截断（0.5 kg 曾变 0 而抛错）"""
        result = await calculate_unit_consumption(10.0, 0.5)
        assert result == 20.0

    async def test_zero_production_raises_error(self) -> None:
        """产量为0应抛出异常"""
        with pytest.raises(ValueError, match="产量必须为正数"):
            await calculate_unit_consumption(1000.0, 0)

    async def test_negative_production_raises_error(self) -> None:
        """负数产量应抛出异常"""
        with pytest.raises(ValueError, match="产量必须为正数"):
            await calculate_unit_consumption(1000.0, -100)

    async def test_single_unit_production(self) -> None:
        """产量为1的边界情况"""
        result = await calculate_unit_consumption(500.0, 1)
        assert result == 500.0


class TestDeviationRateCalculation:
    """测试偏差率计算"""

    async def test_positive_deviation(self) -> None:
        """正偏差（超标）"""
        result = calculate_deviation_rate(2.5, 2.3)
        assert result == 8.7

    async def test_negative_deviation(self) -> None:
        """负偏差（优于目标）"""
        result = calculate_deviation_rate(2.1, 2.3)
        assert result == -8.7

    async def test_zero_deviation(self) -> None:
        """无偏差"""
        result = calculate_deviation_rate(2.3, 2.3)
        assert result == 0.0

    async def test_large_deviation(self) -> None:
        """大偏差"""
        result = calculate_deviation_rate(3.0, 2.0)
        assert result == 50.0

    async def test_zero_target_raises_error(self) -> None:
        """目标值为0应抛出异常"""
        with pytest.raises(ValueError, match="目标值必须为正数"):
            calculate_deviation_rate(2.5, 0)


class TestDeviationStatus:
    """测试偏差状态判定"""

    async def test_normal_status(self) -> None:
        """偏差 ≤ 5% 为 normal"""
        assert determine_deviation_status(5.0) == "normal"
        assert determine_deviation_status(-5.0) == "normal"
        assert determine_deviation_status(0.0) == "normal"
        assert determine_deviation_status(3.5) == "normal"

    async def test_warning_status(self) -> None:
        """5% < 偏差 ≤ 15% 为 warning"""
        assert determine_deviation_status(5.01) == "warning"
        assert determine_deviation_status(15.0) == "warning"
        assert determine_deviation_status(-10.0) == "warning"

    async def test_critical_status(self) -> None:
        """偏差 > 15% 为 critical"""
        assert determine_deviation_status(15.01) == "critical"
        assert determine_deviation_status(30.0) == "critical"
        assert determine_deviation_status(-20.0) == "critical"

    async def test_unknown_status(self) -> None:
        """None 返回 unknown"""
        assert determine_deviation_status(None) == "unknown"


def _mock_db(conv_record: Any = None) -> AsyncSession:
    """构造 db.execute 返回指定折算系数记录的 AsyncSession 替身"""
    result = MagicMock()
    result.scalars.return_value.first.return_value = conv_record
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    return cast(AsyncSession, db)


@contextmanager
def _patched_energy_source(total_energy: float) -> Iterator[None]:
    """屏蔽 prepare_ai_analysis_data 的车间/能耗/目标查询，保留折算与计算真实路径"""
    with (
        patch(
            "app.modules.energy.service.get_workshop_by_id",
            AsyncMock(return_value=SimpleNamespace(name="装配车间A")),
        ),
        patch("app.modules.energy.service.get_target", AsyncMock(return_value=None)),
        patch(
            "app.modules.energy.service.repo.get_monthly_energy_total",
            AsyncMock(return_value=total_energy),
        ),
    ):
        yield


class TestAIPromptConstruction:
    """测试 AI Prompt 构造"""

    async def test_prompt_with_target(self) -> None:
        """有目标值时的 Prompt"""
        analysis_data = {
            "workshop_name": "装配车间A",
            "analysis_month": "2026-08",
            "total_energy_kwh": 30000.0,
            "manual_production": 12000,
            "converted_production": 12000.0,
            "production_details": [
                {"product_name": "测试产品A", "quantity": 10000, "factor": 1.0, "converted_qty": 10000},
                {"product_name": "测试产品B", "quantity": 2500, "factor": 0.8, "converted_qty": 2000},
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
        assert "测试产品A" in prompt
        assert "测试产品B" in prompt

    async def test_prompt_without_target(self) -> None:
        """无目标值时的 Prompt"""
        analysis_data = {
            "workshop_name": "装配车间A",
            "analysis_month": "2026-08",
            "total_energy_kwh": 30000.0,
            "manual_production": 12000,
            "converted_production": 12000.0,
            "production_details": [
                {"product_name": "测试产品A", "quantity": 10000, "factor": 1.0, "converted_qty": 10000},
                {"product_name": "测试产品B", "quantity": 2500, "factor": 0.8, "converted_qty": 2000},
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
        assert "测试产品A" in prompt

    async def test_prompt_json_format_requirement(self) -> None:
        """Prompt 应要求 JSON 格式输出"""
        analysis_data = {
            "converted_production": 12000.0,
            "production_details": [
                {"product_name": "Test", "quantity": 100, "factor": 1.0, "converted_qty": 100},
            ],
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


class TestAIAnalysisDataContract:
    """prepare_ai_analysis_data 的产出必须能被 construct_ai_prompt 消费

    两者曾因 product_name / name 键名不一致而 100% 抛 KeyError，当时测试手写
    fixture 与读方对齐、未走真实生产者，导致测试全绿而生产全挂。
    """

    async def test_producer_output_renders_in_prompt(self) -> None:
        workshop_id: UUID = uuid4()
        with _patched_energy_source(30000.0):
            analysis_data = await prepare_ai_analysis_data(
                _mock_db(),
                workshop_id,
                "2026-08",
                [
                    {"product_name": "测试产品A", "quantity": 10000},
                    {"product_name": "测试产品B", "quantity": 2500},
                ],
            )
            prompt = construct_ai_prompt(analysis_data)

        assert [d["product_name"] for d in analysis_data["production_details"]] == ["测试产品A", "测试产品B"]
        assert "测试产品A" in prompt
        assert "测试产品B" in prompt
        assert analysis_data["converted_production"] == 12500.0
        assert analysis_data["actual_unit_consumption"] == 2.4
        assert analysis_data["deviation_status"] == "unknown"

    async def test_conversion_factor_applied(self) -> None:
        """命中折算系数记录时按系数折算，并写入 prompt"""
        workshop_id: UUID = uuid4()
        conv = SimpleNamespace(conversion_factor=0.5)
        with _patched_energy_source(30000.0):
            analysis_data = await prepare_ai_analysis_data(
                _mock_db(conv),
                workshop_id,
                "2026-08",
                [{"product_name": "测试产品A", "quantity": 10000}],
            )
            prompt = construct_ai_prompt(analysis_data)

        assert analysis_data["production_details"][0]["factor"] == 0.5
        assert analysis_data["converted_production"] == 5000.0
        assert analysis_data["actual_unit_consumption"] == 6.0
        assert "0.5" in prompt

    async def test_fractional_production_completes(self) -> None:
        """折算产量小于 1 时不得因截断而归零报错"""
        workshop_id: UUID = uuid4()
        with _patched_energy_source(10.0):
            analysis_data = await prepare_ai_analysis_data(
                _mock_db(),
                workshop_id,
                "2026-08",
                [{"product_name": "测试产品A", "quantity": 0.5}],
            )
            prompt = construct_ai_prompt(analysis_data)

        assert analysis_data["actual_unit_consumption"] == 20.0
        assert "测试产品A" in prompt


class TestAISuggestionFallback:
    """AI 建议的降级与 LLM 输出收敛

    旧实现用 except Exception 兜住一切并把 str(e) 直接写进 summary，
    因此键名 KeyError 会以 "AI 分析失败: 'name'" 的形式漏到用户界面。
    """

    @staticmethod
    def _production_items() -> list[dict[str, Any]]:
        return [{"product_name": "测试产品A", "quantity": 10000}]

    async def test_llm_error_degrades_without_leaking_detail(self) -> None:
        from app.core.llm.exceptions import LLMOutputError
        from app.modules.energy.service import analyze_energy_v2

        with (
            _patched_energy_source(30000.0),
            patch(
                "app.modules.energy.service.llm_client.chat_json",
                AsyncMock(side_effect=LLMOutputError("provider exploded with secret token")),
            ),
        ):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        suggestion = result["ai_suggestion"]
        assert suggestion.summary == "AI 分析暂时不可用，请人工审核"
        assert suggestion.confidence_level == "low"
        assert suggestion.recommendations == []
        assert "secret token" not in suggestion.summary

    async def test_llm_output_normalized_to_contract(self) -> None:
        from app.modules.energy.service import analyze_energy_v2

        llm_payload = {
            "summary": "单耗正常",
            "detailed_analysis": "分析内容",
            "recommendations": [" 建议一 ", "", "建议二"],
            "confidence_level": "HIGH",
        }
        with (
            _patched_energy_source(30000.0),
            patch("app.modules.energy.service.llm_client.chat_json", AsyncMock(return_value=llm_payload)),
        ):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        suggestion = result["ai_suggestion"]
        assert suggestion.confidence_level == "high"
        assert suggestion.recommendations == ["建议一", "建议二"]

    async def test_unknown_confidence_and_non_list_recommendations(self) -> None:
        from app.modules.energy.service import analyze_energy_v2

        llm_payload = {
            "summary": "s",
            "detailed_analysis": "d",
            "recommendations": "单条建议不是数组",
            "confidence_level": "very-certain",
        }
        with (
            _patched_energy_source(30000.0),
            patch("app.modules.energy.service.llm_client.chat_json", AsyncMock(return_value=llm_payload)),
        ):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        suggestion = result["ai_suggestion"]
        assert suggestion.confidence_level == "medium"
        assert suggestion.recommendations == ["单条建议不是数组"]

    async def test_recommendation_objects_flatten_to_readable_text(self) -> None:
        """网关模型实际会把单条建议返回成对象，直接 str() 会把 Python dict repr 渲染到页面。"""
        from app.modules.energy.service import analyze_energy_v2

        llm_payload = {
            "summary": "s",
            "detailed_analysis": "d",
            "recommendations": [
                {"建议": "加装分项计量", "具体措施": "按工序加装电表", "预期效果": "识别 1-2% 节能空间"},
                {"建议": "优化排程", "具体措施": "", "预期效果": "  "},
                "",
            ],
            "confidence_level": "medium",
        }
        with (
            _patched_energy_source(30000.0),
            patch("app.modules.energy.service.llm_client.chat_json", AsyncMock(return_value=llm_payload)),
        ):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        assert result["ai_suggestion"].recommendations == [
            "加装分项计量 — 按工序加装电表 — 识别 1-2% 节能空间",
            "优化排程",
        ]

    async def test_partial_output_still_usable(self) -> None:
        """模型漏掉 confidence_level / recommendations 时不能把已有结论一起丢弃。"""
        from app.modules.energy.service import analyze_energy_v2

        llm_payload = {
            "summary": "单耗正常",
            "detailed_analysis": "分析内容",
            "recommendations": None,
            "confidence_level": None,
        }
        chat_json = AsyncMock(return_value=llm_payload)
        with _patched_energy_source(30000.0), patch("app.modules.energy.service.llm_client.chat_json", chat_json):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        # 传入 expected_keys 会让 chat_json 对缺字段直接抛错，可用结论会被整体丢弃
        assert chat_json.await_args is not None
        assert "expected_keys" not in chat_json.await_args.kwargs
        suggestion = result["ai_suggestion"]
        assert suggestion.summary == "单耗正常"
        assert suggestion.detailed_analysis == "分析内容"
        assert suggestion.recommendations == []
        assert suggestion.confidence_level == "medium"
        assert suggestion.summary != "AI 分析暂时不可用，请人工审核"

    async def test_gateway_json_object_envelope_is_unwrapped(self) -> None:
        """网关对 response_format=json_object 会套 {"type":"json_object","content":{...}}，
        按顶层取字段会全部落空并误判为 AI 不可用。"""
        from app.modules.energy.service import analyze_energy_v2

        llm_payload = {
            "type": "json_object",
            "content": {
                "summary": "单耗优于目标",
                "detailed_analysis": "本月总能耗低于目标水平",
                "recommendations": [{"建议": "加装分项计量", "预期效果": "定位高耗能工序"}],
                "confidence_level": "medium",
            },
        }
        with (
            _patched_energy_source(30000.0),
            patch("app.modules.energy.service.llm_client.chat_json", AsyncMock(return_value=llm_payload)),
        ):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        suggestion = result["ai_suggestion"]
        assert suggestion.summary == "单耗优于目标"
        assert suggestion.detailed_analysis == "本月总能耗低于目标水平"
        assert suggestion.recommendations == ["加装分项计量 — 定位高耗能工序"]
        assert suggestion.confidence_level == "medium"

    async def test_envelope_without_analysis_fields_degrades(self) -> None:
        from app.modules.energy.service import analyze_energy_v2

        with (
            _patched_energy_source(30000.0),
            patch(
                "app.modules.energy.service.llm_client.chat_json",
                AsyncMock(return_value={"type": "json_object", "result": {"foo": "bar"}}),
            ),
        ):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        assert result["ai_suggestion"].summary == "AI 分析暂时不可用，请人工审核"
        assert result["ai_suggestion"].confidence_level == "low"

    async def test_blank_summary_and_analysis_degrades(self) -> None:
        from app.modules.energy.service import analyze_energy_v2

        llm_payload = {"summary": "  ", "detailed_analysis": "", "recommendations": ["建议一"]}
        with (
            _patched_energy_source(30000.0),
            patch("app.modules.energy.service.llm_client.chat_json", AsyncMock(return_value=llm_payload)),
        ):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        assert result["ai_suggestion"].summary == "AI 分析暂时不可用，请人工审核"

    async def test_only_detailed_analysis_is_still_shown(self) -> None:
        """模型漏掉 summary 时不能整块丢弃已经拿到的详细分析。"""
        from app.modules.energy.service import analyze_energy_v2

        llm_payload = {"summary": None, "detailed_analysis": "本月单耗低于目标", "recommendations": ["保持现状"]}
        with (
            _patched_energy_source(30000.0),
            patch("app.modules.energy.service.llm_client.chat_json", AsyncMock(return_value=llm_payload)),
        ):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        suggestion = result["ai_suggestion"]
        assert suggestion.summary == ""
        assert suggestion.detailed_analysis == "本月单耗低于目标"
        assert suggestion.recommendations == ["保持现状"]

    async def test_non_dict_output_degrades_instead_of_crashing(self) -> None:
        """chat_json 兜不住非对象输出（模型返回裸字符串/数组），不能让它冒成 500。"""
        from app.modules.energy.service import analyze_energy_v2

        with (
            _patched_energy_source(30000.0),
            patch("app.modules.energy.service.llm_client.chat_json", AsyncMock(return_value="只有一段文本")),
        ):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=True
            )

        assert result["ai_suggestion"].summary == "AI 分析暂时不可用，请人工审核"

    async def test_ai_suggestion_skipped_when_not_requested(self) -> None:
        from app.modules.energy.service import analyze_energy_v2

        chat_json = AsyncMock()
        with _patched_energy_source(30000.0), patch("app.modules.energy.service.llm_client.chat_json", chat_json):
            result = await analyze_energy_v2(
                _mock_db(), uuid4(), "2026-08", self._production_items(), include_ai_suggestion=False
            )

        assert result["ai_suggestion"] is None
        chat_json.assert_not_awaited()
