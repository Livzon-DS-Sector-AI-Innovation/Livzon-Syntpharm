"""Integration tests for the AI three-layer query architecture.

Run with: .venv/Scripts/python tests/test_ai_integration.py

This script tests the actual LLM-based planner and mocked executor
to verify data flow correctness.
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is on path
sys.path.insert(0, "e:\\czl\\xbj2\\dazah-backend")

import openai

from app.platform.ai.executor import (
    StepResult,
    _execute_single_query,
    format_step_results,
)
from app.platform.ai.planner import generate_plan
from app.platform.ai.schemas import PlanStep, SubQuery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

results = {"pass": 0, "fail": 0}


def assert_true(condition: bool, msg: str) -> None:
    if not condition:
        raise AssertionError(msg)


def run_test(name: str, test_fn):
    try:
        test_fn()
        print(f"  {PASS} {name}")
        results["pass"] += 1
    except AssertionError as exc:
        print(f"  {FAIL} {name}: {exc}")
        results["fail"] += 1
    except Exception as exc:
        print(f"  {FAIL} {name}: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        results["fail"] += 1


async def run_async_test(name: str, test_fn):
    try:
        await test_fn()
        print(f"  {PASS} {name}")
        results["pass"] += 1
    except AssertionError as exc:
        print(f"  {FAIL} {name}: {exc}")
        results["fail"] += 1
    except Exception as exc:
        print(f"  {FAIL} {name}: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        results["fail"] += 1


# ---------------------------------------------------------------------------
# Round 1 — Basic single-step queries (Planner with real LLM)
# ---------------------------------------------------------------------------

async def round1_tests(client: openai.AsyncOpenAI):
    print("\n=== Round 1: Basic single-step queries ===")

    # Case 1: group_count distribution
    async def test_01():
        plan = await generate_plan(client, "在职员工学历分布")
        assert_true(plan is not None, "plan should not be None")
        assert_true(plan.needs_data is True, "needs_data should be True")
        assert_true(len(plan.steps) >= 1, "should have at least 1 step")
        step = plan.steps[0]
        assert_true(step.mode == "static", f"expected static, got {step.mode}")
        assert_true(len(step.parallel_queries) >= 1, "should have at least 1 query")
        q = step.parallel_queries[0]
        assert_true(q.action == "group_count", f"expected group_count, got {q.action}")
        assert_true(q.group_by == "education", f"expected education, got {q.group_by}")
        assert_true(q.filters.get("status") == "在职", "should filter by 在职")
        print(f"    -> Plan: {q.action} by {q.group_by}, filters={q.filters}")

    await run_async_test("01 在职员工学历分布 → group_count", test_01)

    # Case 2: simple count
    async def test_02():
        plan = await generate_plan(client, "公司一共有多少人")
        assert_true(plan is not None, "plan should not be None")
        assert_true(plan.needs_data is True, "needs_data should be True")
        q = plan.steps[0].parallel_queries[0]
        assert_true(q.action == "count", f"expected count, got {q.action}")
        print(f"    -> Plan: {q.action}, filters={q.filters}")

    await run_async_test("02 公司一共有多少人 → count", test_02)

    # Case 3: employee list query
    async def test_03():
        plan = await generate_plan(client, "生产部有哪些工程师")
        assert_true(plan is not None, "plan should not be None")
        q = plan.steps[0].parallel_queries[0]
        assert_true(q.action == "query", f"expected query, got {q.action}")
        assert_true("生产部" in str(q.filters.get("department", "")), "should filter by 生产部")
        print(f"    -> Plan: {q.action}, filters={q.filters}")

    await run_async_test("03 生产部有哪些工程师 → query", test_03)

    # Case 4: get_distinct
    async def test_04():
        plan = await generate_plan(client, "有哪些部门")
        assert_true(plan is not None, "plan should not be None")
        q = plan.steps[0].parallel_queries[0]
        assert_true(q.action == "get_distinct", f"expected get_distinct, got {q.action}")
        assert_true(q.group_by == "department", f"expected department, got {q.group_by}")
        print(f"    -> Plan: {q.action} {q.group_by}")

    await run_async_test("04 有哪些部门 → get_distinct", test_04)

    # Case 5: multi-filter count
    async def test_05():
        plan = await generate_plan(client, "30岁以上本科在职员工有多少人")
        assert_true(plan is not None, "plan should not be None")
        q = plan.steps[0].parallel_queries[0]
        assert_true(q.action == "count", f"expected count, got {q.action}")
        f = q.filters
        assert_true(f.get("age_min") == 30 or f.get("age_max") == 30, "should have age filter")
        assert_true("本科" in str(f.get("education", "")), "should filter by 本科")
        assert_true("在职" in str(f.get("status", "")), "should filter by 在职")
        print(f"    -> Plan: {q.action}, filters={f}")

    await run_async_test("05 30岁以上本科在职员工 → count with filters", test_05)


# ---------------------------------------------------------------------------
# Round 2 — Multi-step / parallel / dynamic queries
# ---------------------------------------------------------------------------

async def round2_tests(client: openai.AsyncOpenAI):
    print("\n=== Round 2: Multi-step / parallel / dynamic queries ===")

    # Case 6: dynamic multi-step
    async def test_06():
        plan = await generate_plan(client, "每个部门的学历分布")
        assert_true(plan is not None, "plan should not be None")
        assert_true(len(plan.steps) >= 1, "should have at least 1 step")

        # Could be 1-step group_count or 2-step dynamic
        if len(plan.steps) == 1:
            q = plan.steps[0].parallel_queries[0]
            assert_true(q.action == "group_count", f"expected group_count, got {q.action}")
            print(f"    -> Plan: 1-step {q.action} by {q.group_by}")
        else:
            assert_true(plan.steps[0].mode == "static", "step 1 should be static")
            assert_true(plan.steps[1].mode == "dynamic", "step 2 should be dynamic")
            print(f"    -> Plan: 2-step {plan.steps[0].mode} + {plan.steps[1].mode}")

    await run_async_test("06 每个部门的学历分布 → multi-step", test_06)

    # Case 7: parallel queries in one step
    async def test_07():
        plan = await generate_plan(client, "生产部和研发部各有多少人")
        assert_true(plan is not None, "plan should not be None")
        queries = plan.steps[0].parallel_queries
        assert_true(len(queries) >= 1, "should have at least 1 query")

        if len(queries) == 1 and queries[0].action == "group_count":
            print(f"    -> Plan: 1-step group_count by department")
        else:
            assert_true(len(queries) == 2, "expected 2 parallel queries")
            assert_true(all(q.action == "count" for q in queries), "both should be count")
            print(f"    -> Plan: 2 parallel count queries")

    await run_async_test("07 生产部和研发部各有多少人 → parallel", test_07)

    # Case 8: mixed parallel
    async def test_08():
        plan = await generate_plan(client, "各部门人数及性别分布")
        assert_true(plan is not None, "plan should not be None")
        queries = plan.steps[0].parallel_queries
        assert_true(len(queries) >= 1, "should have at least 1 query")
        print(f"    -> Plan: {len(queries)} parallel queries: {[q.action for q in queries]}")

    await run_async_test("08 各部门人数及性别分布 → mixed parallel", test_08)


# ---------------------------------------------------------------------------
# Round 3 — Edge cases
# ---------------------------------------------------------------------------

async def round3_tests(client: openai.AsyncOpenAI):
    print("\n=== Round 3: Edge cases ===")

    # Case 9: no data needed
    async def test_09():
        plan = await generate_plan(client, "你好")
        assert_true(plan is not None, "plan should not be None")
        assert_true(plan.needs_data is False, "needs_data should be False")
        print(f"    -> Plan: needs_data=False")

    await run_async_test("09 你好 → no data needed", test_09)

    # Case 10: executor data flow verification
    def test_10():
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
        assert_true("步骤1" in formatted, "should contain step label")
        assert_true("本科：25人" in formatted, "should contain 本科 count")
        assert_true("硕士：10人" in formatted, "should contain 硕士 count")
        assert_true("共计：35人" in formatted, "should contain total")
        print(f"    -> Formatted output contains correct data")

    run_test("10 Executor formatting → correct data flow", test_10)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    from app.core.config import get_settings

    settings = get_settings()
    client = openai.AsyncOpenAI(
        api_key=settings.MOONSHOT_API_KEY,
        base_url="https://api.moonshot.cn/v1",
    )

    print(f"Testing with model: kimi-k2.5")
    print(f"Date: {date.today().isoformat()}")

    await round1_tests(client)
    await round2_tests(client)
    await round3_tests(client)

    print("\n=== Results ===")
    print(f"  Passed: {results['pass']}")
    print(f"  Failed: {results['fail']}")

    if results["fail"] > 0:
        sys.exit(1)
    print("\nAll rounds passed!")


if __name__ == "__main__":
    asyncio.run(main())
