"""Tests for the AI three-layer query architecture.

Test strategy: three rounds of testing.
- Round 1 (Basic): 5 test cases covering single-step queries.
- Round 2 (Advanced): 3 test cases covering multi-step / parallel / dynamic queries.
- Round 3 (Edge): 2 test cases covering edge cases and fallbacks.

Each round must pass before moving to the next.
If a round fails, adjust prompts and restart from Round 1.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.platform.ai.executor import (
    StepResult,
    _execute_single_query,
    execute_plan,
    format_step_results,
)
from app.platform.ai.planner import _parse_plan, generate_plan
from app.platform.ai.schemas import PlanStep, QueryPlan, SubQuery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_llm_response(content: dict) -> MagicMock:
    """Build a mocked OpenAI chat completion response."""
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(content, ensure_ascii=False)
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI AsyncOpenAI client."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# Round 1 — Basic single-step queries (5 cases)
# ---------------------------------------------------------------------------

class TestRound1BasicQueries:
    """Round 1: Planner should generate correct single-step static plans."""

    @pytest.mark.asyncio
    async def test_01_group_count_distribution(self, mock_openai_client):
        """Case 1: '在职员工学历分布' → single group_count step."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": True,
                "steps": [
                    {
                        "step": 1,
                        "mode": "static",
                        "description": "按学历分组统计在职员工人数",
                        "parallel_queries": [
                            {
                                "action": "group_count",
                                "description": "在职员工学历分布",
                                "group_by": "education",
                                "filters": {"status": "在职"},
                            }
                        ],
                        "reasoning": "分布类问题可直接用group_count一步完成",
                    }
                ],
                "reasoning": "用户想知道在职员工的学历分布",
            }
        )

        plan = await generate_plan(mock_openai_client, "在职员工学历分布")

        assert plan is not None
        assert plan.needs_data is True
        assert len(plan.steps) == 1
        assert plan.steps[0].mode == "static"
        assert plan.steps[0].parallel_queries[0].action == "group_count"
        assert plan.steps[0].parallel_queries[0].group_by == "education"
        assert plan.steps[0].parallel_queries[0].filters == {"status": "在职"}

    @pytest.mark.asyncio
    async def test_02_simple_count(self, mock_openai_client):
        """Case 2: '公司一共有多少人' → single count step."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": True,
                "steps": [
                    {
                        "step": 1,
                        "mode": "static",
                        "description": "统计公司总人数",
                        "parallel_queries": [
                            {
                                "action": "count",
                                "description": "公司总人数",
                                "filters": {},
                            }
                        ],
                        "reasoning": "用户只想知道总数",
                    }
                ],
                "reasoning": "用户问公司总人数",
            }
        )

        plan = await generate_plan(mock_openai_client, "公司一共有多少人")

        assert plan is not None
        assert plan.steps[0].parallel_queries[0].action == "count"
        assert plan.steps[0].parallel_queries[0].filters == {}

    @pytest.mark.asyncio
    async def test_03_employee_list_query(self, mock_openai_client):
        """Case 3: '生产部有哪些工程师' → single query step."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": True,
                "steps": [
                    {
                        "step": 1,
                        "mode": "static",
                        "description": "查询生产部的工程师名单",
                        "parallel_queries": [
                            {
                                "action": "query",
                                "description": "生产部工程师名单",
                                "filters": {"department": "生产部", "position": "工程师"},
                                "limit": 50,
                            }
                        ],
                        "reasoning": "用户想看名单",
                    }
                ],
                "reasoning": "用户想看生产部工程师名单",
            }
        )

        plan = await generate_plan(mock_openai_client, "生产部有哪些工程师")

        assert plan.steps[0].parallel_queries[0].action == "query"
        assert plan.steps[0].parallel_queries[0].filters["department"] == "生产部"
        assert plan.steps[0].parallel_queries[0].limit == 50

    @pytest.mark.asyncio
    async def test_04_get_distinct_values(self, mock_openai_client):
        """Case 4: '有哪些部门' → single get_distinct step."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": True,
                "steps": [
                    {
                        "step": 1,
                        "mode": "static",
                        "description": "获取所有部门名称",
                        "parallel_queries": [
                            {
                                "action": "get_distinct",
                                "description": "所有部门",
                                "group_by": "department",
                                "filters": {},
                            }
                        ],
                        "reasoning": "用户想知道有哪些部门",
                    }
                ],
                "reasoning": "获取部门列表",
            }
        )

        plan = await generate_plan(mock_openai_client, "有哪些部门")

        assert plan.steps[0].parallel_queries[0].action == "get_distinct"
        assert plan.steps[0].parallel_queries[0].group_by == "department"

    @pytest.mark.asyncio
    async def test_05_multi_filter_count(self, mock_openai_client):
        """Case 5: '30岁以上本科在职员工有多少人' → count with multiple filters."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": True,
                "steps": [
                    {
                        "step": 1,
                        "mode": "static",
                        "description": "统计30岁以上本科在职员工人数",
                        "parallel_queries": [
                            {
                                "action": "count",
                                "description": "30岁以上本科在职员工人数",
                                "filters": {
                                    "age_min": 30,
                                    "education": "本科",
                                    "status": "在职",
                                },
                            }
                        ],
                        "reasoning": "多条件计数",
                    }
                ],
                "reasoning": "用户问多条件人数",
            }
        )

        plan = await generate_plan(mock_openai_client, "30岁以上本科在职员工有多少人")

        filters = plan.steps[0].parallel_queries[0].filters
        assert filters["age_min"] == 30
        assert filters["education"] == "本科"
        assert filters["status"] == "在职"


# ---------------------------------------------------------------------------
# Round 2 — Multi-step / parallel / dynamic queries (3 cases)
# ---------------------------------------------------------------------------

class TestRound2AdvancedQueries:
    """Round 2: Planner should generate multi-step plans with parallel/dynamic steps."""

    @pytest.mark.asyncio
    async def test_06_dynamic_multi_step(self, mock_openai_client):
        """Case 6: '每个部门的学历分布' → static get_distinct + dynamic group_count."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": True,
                "steps": [
                    {
                        "step": 1,
                        "mode": "static",
                        "description": "获取所有部门名称",
                        "parallel_queries": [
                            {
                                "action": "get_distinct",
                                "description": "所有部门",
                                "group_by": "department",
                                "filters": {},
                            }
                        ],
                        "reasoning": "先获取部门列表",
                    },
                    {
                        "step": 2,
                        "mode": "dynamic",
                        "description": "对每个部门查询在职员工的学历分布",
                        "reasoning": "基于部门列表分别统计",
                    },
                ],
                "reasoning": "用户想知道每个部门的学历分布",
            }
        )

        plan = await generate_plan(mock_openai_client, "每个部门的学历分布")

        assert len(plan.steps) == 2
        assert plan.steps[0].mode == "static"
        assert plan.steps[0].parallel_queries[0].action == "get_distinct"
        assert plan.steps[1].mode == "dynamic"
        assert plan.steps[1].parallel_queries is None

    @pytest.mark.asyncio
    async def test_07_parallel_queries_in_one_step(self, mock_openai_client):
        """Case 7: '生产部和研发部各有多少人' → static step with 2 parallel count queries."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": True,
                "steps": [
                    {
                        "step": 1,
                        "mode": "static",
                        "description": "查询生产部和研发部的人数",
                        "parallel_queries": [
                            {
                                "action": "count",
                                "description": "生产部人数",
                                "filters": {"department": "生产部"},
                            },
                            {
                                "action": "count",
                                "description": "研发部人数",
                                "filters": {"department": "研发部"},
                            },
                        ],
                        "reasoning": "两个部门的人数可以并行查询",
                    }
                ],
                "reasoning": "用户想知道两个部门的人数",
            }
        )

        plan = await generate_plan(mock_openai_client, "生产部和研发部各有多少人")

        assert len(plan.steps[0].parallel_queries) == 2
        assert plan.steps[0].parallel_queries[0].filters["department"] == "生产部"
        assert plan.steps[0].parallel_queries[1].filters["department"] == "研发部"

    @pytest.mark.asyncio
    async def test_08_mixed_parallel(self, mock_openai_client):
        """Case 8: '各部门人数及性别分布' → group_count + count in parallel."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": True,
                "steps": [
                    {
                        "step": 1,
                        "mode": "static",
                        "description": "统计各部门人数及性别分布",
                        "parallel_queries": [
                            {
                                "action": "group_count",
                                "description": "各部门人数",
                                "group_by": "department",
                                "filters": {},
                            },
                            {
                                "action": "group_count",
                                "description": "性别分布",
                                "group_by": "gender",
                                "filters": {},
                            },
                        ],
                        "reasoning": "部门人数和性别分布可以并行统计",
                    }
                ],
                "reasoning": "用户想同时了解部门人数和性别分布",
            }
        )

        plan = await generate_plan(mock_openai_client, "各部门人数及性别分布")

        queries = plan.steps[0].parallel_queries
        assert len(queries) == 2
        assert queries[0].group_by == "department"
        assert queries[1].group_by == "gender"


# ---------------------------------------------------------------------------
# Round 3 — Edge cases and fallbacks (2 cases)
# ---------------------------------------------------------------------------

class TestRound3EdgeCases:
    """Round 3: Edge cases — no data needed, fallback parsing, etc."""

    @pytest.mark.asyncio
    async def test_09_no_data_needed(self, mock_openai_client):
        """Case 9: '你好' → needs_data=false."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": False,
                "reasoning": "这是问候语，不需要查询数据",
            }
        )

        plan = await generate_plan(mock_openai_client, "你好")

        assert plan is not None
        assert plan.needs_data is False
        assert len(plan.steps) == 0

    @pytest.mark.asyncio
    async def test_10_plan_parsing_invalid_action(self, mock_openai_client):
        """Case 10: Planner returns invalid action → should be filtered out."""
        mock_openai_client.chat.completions.create.return_value = _mock_llm_response(
            {
                "needs_data": True,
                "steps": [
                    {
                        "step": 1,
                        "mode": "static",
                        "description": "测试",
                        "parallel_queries": [
                            {
                                "action": "invalid_action",
                                "description": "无效操作",
                            },
                            {
                                "action": "count",
                                "description": "有效操作",
                                "filters": {},
                            },
                        ],
                        "reasoning": "测试过滤",
                    }
                ],
                "reasoning": "测试",
            }
        )

        plan = await generate_plan(mock_openai_client, "测试")

        # Invalid action should be filtered out, leaving only the valid one
        assert len(plan.steps[0].parallel_queries) == 1
        assert plan.steps[0].parallel_queries[0].action == "count"


# ---------------------------------------------------------------------------
# Executor tests (data flow verification)
# ---------------------------------------------------------------------------

class TestExecutorDataFlow:
    """Verify that the executor correctly formats data for the main AI."""

    @pytest.mark.asyncio
    async def test_executor_group_count_formatting(self, mock_session):
        """Verify group_count results are formatted correctly."""
        with patch(
            "app.platform.ai.executor.group_count_employees",
            new_callable=AsyncMock,
            return_value=[
                {"value": "本科", "count": 25},
                {"value": "硕士", "count": 10},
            ],
        ):
            query = SubQuery(
                action="group_count",
                description="在职员工学历分布",
                group_by="education",
                filters={"status": "在职"},
            )
            result = await _execute_single_query(mock_session, query)

            assert result["action"] == "group_count"
            assert len(result["groups"]) == 2
            assert result["groups"][0]["value"] == "本科"
            assert result["groups"][0]["count"] == 25

    def test_format_step_results_group_count(self):
        """Verify natural-language formatting of group_count results."""
        step = PlanStep(
            step=1,
            mode="static",
            description="按学历分组统计在职员工人数",
            parallel_queries=[],
        )
        step_result = StepResult(
            step=step,
            results=[
                {
                    "action": "group_count",
                    "description": "在职员工学历分布",
                    "group_by": "education",
                    "groups": [
                        {"value": "本科", "count": 25},
                        {"value": "硕士", "count": 10},
                    ],
                }
            ],
        )

        formatted = format_step_results([step_result])

        assert "步骤1" in formatted
        assert "本科：25人" in formatted
        assert "硕士：10人" in formatted
        assert "共计：35人" in formatted

    def test_format_step_results_count(self):
        """Verify natural-language formatting of count results."""
        step = PlanStep(
            step=1,
            mode="static",
            description="统计公司总人数",
            parallel_queries=[],
        )
        step_result = StepResult(
            step=step,
            results=[
                {
                    "action": "count",
                    "description": "公司总人数",
                    "count": 150,
                }
            ],
        )

        formatted = format_step_results([step_result])

        assert "公司总人数：150人" in formatted
