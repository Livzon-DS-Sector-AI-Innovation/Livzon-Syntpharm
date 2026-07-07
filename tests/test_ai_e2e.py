"""End-to-end functional test for the AI three-layer query architecture.

Runs 10 different questions through the complete pipeline:
    User Question -> Planner -> Executor -> Formatter

Mocks database queries so no real DB is needed.
Run with: .venv/Scripts/python tests/test_ai_e2e.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date
from unittest.mock import AsyncMock, patch

sys.path.insert(0, "e:\\czl\\xbj2\\dazah-backend")

import openai

from app.platform.ai.executor import execute_plan, format_step_results
from app.platform.ai.planner import generate_plan


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

MOCK_GROUP_COUNT = {
    ("education", frozenset({("status", "在职")})): [
        {"value": "本科", "count": 25},
        {"value": "硕士", "count": 10},
        {"value": "大专", "count": 8},
        {"value": "高中", "count": 5},
    ],
    ("department", frozenset()): [
        {"value": "生产部", "count": 30},
        {"value": "研发部", "count": 20},
        {"value": "质量部", "count": 15},
    ],
    ("gender", frozenset()): [
        {"value": "男", "count": 40},
        {"value": "女", "count": 25},
    ],
}

MOCK_COUNT = {
    frozenset(): 150,
    frozenset({("status", "在职")}): 120,
    frozenset({("department", "生产部")}): 30,
    frozenset({("department", "研发部")}): 20,
    frozenset({("age_min", 30), ("education", "本科"), ("status", "在职")}): 35,
}

MOCK_DISTINCT = {
    ("department", frozenset()): ["生产部", "研发部", "质量部", "行政部"],
    ("education", frozenset({("status", "在职")})): ["本科", "硕士", "大专", "高中"],
}

MOCK_EMPLOYEES = [
    {
        "name": "张三",
        "employee_number": "E001",
        "department": "生产部",
        "position": "工程师",
        "status": "在职",
        "education": "本科",
        "gender": "男",
        "age": 32,
    },
    {
        "name": "李四",
        "employee_number": "E002",
        "department": "生产部",
        "position": "工程师",
        "status": "在职",
        "education": "硕士",
        "gender": "女",
        "age": 28,
    },
    {
        "name": "王五",
        "employee_number": "E003",
        "department": "研发部",
        "position": "高级工程师",
        "status": "在职",
        "education": "硕士",
        "gender": "男",
        "age": 35,
    },
]


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

async def mock_group_count(session, *, group_by: str, filters: dict):
    key = (group_by, frozenset(filters.items()))
    return MOCK_GROUP_COUNT.get(key, [])


async def mock_count(session, filters: dict):
    key = frozenset(filters.items())
    return MOCK_COUNT.get(key, 0)


async def mock_query(session, filters: dict, page: int, page_size: int):
    return MOCK_EMPLOYEES[:page_size], len(MOCK_EMPLOYEES)


async def mock_distinct(session, *, field: str, filters: dict):
    key = (field, frozenset(filters.items()))
    return MOCK_DISTINCT.get(key, [])


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

async def run_question(client: openai.AsyncOpenAI, session, q: str, idx: int):
    print(f"\n{'=' * 60}")
    print(f"【问题 {idx}】{q}")
    print("=" * 60)

    # Layer 1: Planner
    plan = await generate_plan(client, q)
    if plan is None:
        print("  [Planner] 未生成计划（回退到旧逻辑）")
        return

    if not plan.needs_data:
        print(f"  [Planner] needs_data=False，无需查询")
        print(f"  [Planner] reasoning: {plan.reasoning}")
        return

    print(f"  [Planner] 生成 {len(plan.steps)} 步计划")
    for step in plan.steps:
        mode_str = "【静态】" if step.mode == "static" else "【动态】"
        print(f"    步骤{step.step} {mode_str} {step.description}")
        if step.parallel_queries:
            for sq in step.parallel_queries:
                print(f"      -> {sq.action}: {sq.description} filters={sq.filters}")

    # Layer 2: Executor
    with patch("app.platform.ai.executor.group_count_employees", mock_group_count), \
         patch("app.platform.ai.executor.count_employees", mock_count), \
         patch("app.platform.ai.executor.query_employees", mock_query), \
         patch("app.platform.ai.executor.get_distinct_employee_values", mock_distinct):
        results = await execute_plan(session, plan, q, client)

    # Layer 3: Format
    formatted = format_step_results(results)
    print(f"\n  [Formatted Context]\n{formatted}")


async def main():
    from app.core.config import get_settings

    settings = get_settings()
    client = openai.AsyncOpenAI(
        api_key=settings.MOONSHOT_API_KEY,
        base_url="https://api.moonshot.cn/v1",
    )
    session = AsyncMock()

    questions = [
        "在职员工学历分布",
        "公司一共有多少人",
        "生产部有哪些工程师",
        "有哪些部门",
        "30岁以上本科在职员工有多少人",
        "每个部门的学历分布",
        "生产部和研发部各有多少人",
        "各部门人数及性别分布",
        "你好",
        "请列出所有在职员工的姓名",
    ]

    print(f"模型: kimi-k2.5")
    print(f"日期: {date.today().isoformat()}")
    print(f"问题数: {len(questions)}")

    for i, q in enumerate(questions, 1):
        await run_question(client, session, q, i)

    print(f"\n{'=' * 60}")
    print("全部 10 个问题测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
