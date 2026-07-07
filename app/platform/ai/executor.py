"""AI query executor — Layer 2: executes a QueryPlan step by step.

Supports:
- Static steps: run pre-defined parallel queries directly.
- Dynamic steps: ask an LLM to generate parallel queries based on previous results
  AND the original plan, then execute them.
- Parallel execution within each step via asyncio.gather().
"""

from __future__ import annotations

import asyncio
import json
import logging

import openai
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.public_api import (
    count_employees,
    get_distinct_employee_values,
    group_count_employees,
    query_employees,
)
from app.platform.ai.schemas import PlanStep, QueryPlan, SubQuery

logger = logging.getLogger(__name__)

def _get_model() -> str:
    from app.core.config import get_settings
    return get_settings().AI_MODEL or "kimi-k2.5"

_DYNAMIC_SYSTEM_PROMPT = """你是工厂人事系统的「动态查询生成助手」。

## 任务
基于第一层的完整计划目标和已获取的数据，生成当前步骤需要**并行执行**的数据库查询。

## 可用查询操作
- query: 返回员工列表
- count: 返回计数
- group_count: 按字段分组统计
- get_distinct: 获取不重复值

## 可用过滤字段
department, team, position, status, gender, education,
political_status, marital_status, status_category,
age_min, age_max, birth_year_min, birth_year_max,
hire_date_after, hire_date_before,
factory_entry_date_after, factory_entry_date_before,
work_start_date_after, work_start_date_before

## 规则
1. 必须基于「第一层的完整计划」和「已获取的实际数据」生成查询
2. 如果前序结果包含列表值（如部门列表），可以为每个值生成一条查询
3. 多条查询会在同一步骤内并行执行
4. 尽量合并：如果多个值可以用一个 group_count 完成，就不要拆成多个 count
5. 如果不需要更多数据，返回空数组
6. 默认排除待审批员工

## 输出格式（JSON，不要markdown代码块）
{
  "parallel_queries": [
    {
      "action": "group_count",
      "description": "生产部在职员工学历分布",
      "group_by": "education",
      "filters": {"department": "生产部", "status": "在职"}
    }
  ],
  "reasoning": "基于步骤1获取的部门列表，分别统计每个部门的学历分布"
}
"""


class StepResult:
    """Result of executing a single plan step."""

    def __init__(self, step: PlanStep, results: list[dict]) -> None:
        self.step = step
        self.results = results

    def to_dict(self) -> dict:
        return {
            "step": self.step.step,
            "mode": self.step.mode,
            "description": self.step.description,
            "results": self.results,
        }


async def _execute_single_query(
    session: AsyncSession,
    query: SubQuery,
) -> dict:
    """Execute a single SubQuery and return structured result."""
    action = query.action
    filters = query.filters or {}

    try:
        if action == "query":
            employees, total = await query_employees(
                session,
                filters=filters,
                page=1,
                page_size=query.limit or 200,
            )
            return {
                "action": "query",
                "description": query.description,
                "employees": employees,
                "total": total,
            }

        if action == "count":
            total = await count_employees(session, filters=filters)
            return {
                "action": "count",
                "description": query.description,
                "count": total,
            }

        if action == "group_count":
            groups = await group_count_employees(
                session,
                group_by=query.group_by or "",
                filters=filters,
            )
            return {
                "action": "group_count",
                "description": query.description,
                "group_by": query.group_by,
                "groups": groups,
            }

        if action == "get_distinct":
            values = await get_distinct_employee_values(
                session,
                field=query.group_by or "",
                filters=filters,
            )
            return {
                "action": "get_distinct",
                "description": query.description,
                "field": query.group_by,
                "values": values,
            }
    except Exception as exc:
        logger.exception("Query execution failed: %s", exc)
        return {
            "action": action,
            "description": query.description,
            "error": str(exc),
        }

    return {
        "action": action,
        "description": query.description,
        "error": "Unknown action",
    }


async def _execute_parallel_queries(
    session: AsyncSession,
    queries: list[SubQuery],
) -> list[dict]:
    """Execute multiple SubQueries in parallel."""
    if not queries:
        return []

    coros = [_execute_single_query(session, q) for q in queries]
    results = await asyncio.gather(*coros, return_exceptions=True)

    parsed: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            parsed.append({"error": str(r)})
        else:
            parsed.append(r)
    return parsed


async def _generate_dynamic_queries(
    client: openai.AsyncOpenAI,
    user_question: str,
    original_plan: QueryPlan,
    step: PlanStep,
    previous_results: list[StepResult],
) -> list[SubQuery]:
    """Ask LLM to generate parallel queries for a dynamic step."""

    # Build context: original plan + executed results
    plan_context = json.dumps(
        {
            "needs_data": original_plan.needs_data,
            "steps": [
                {
                    "step": s.step,
                    "mode": s.mode,
                    "description": s.description,
                    "reasoning": s.reasoning,
                }
                for s in original_plan.steps
            ],
            "reasoning": original_plan.reasoning,
        },
        ensure_ascii=False,
        indent=2,
    )

    executed_context = json.dumps(
        [r.to_dict() for r in previous_results],
        ensure_ascii=False,
        indent=2,
    )

    user_prompt = (
        f"用户原始问题：{user_question}\n\n"
        f"第一层生成的完整计划（含所有步骤意图）：\n{plan_context}\n\n"
        f"已执行的步骤及结果：\n{executed_context}\n\n"
        f"当前需要执行第 {step.step} 步，意图是：{step.description}\n\n"
        f"请生成接下来需要并行执行的数据库查询。"
    )

    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=_get_model(),
                messages=[
                    {"role": "system", "content": _DYNAMIC_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=1.0,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.warning(
                "Dynamic query generation failed (attempt %d): %s",
                attempt + 1,
                exc,
            )
            if attempt < 2:
                continue
            return []

        raw = response.choices[0].message.content
        if not raw:
            logger.warning(
                "Dynamic query generation empty (attempt %d)", attempt + 1
            )
            if attempt < 2:
                continue
            return []

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "Dynamic query generation invalid JSON (attempt %d)",
                attempt + 1,
            )
            if attempt < 2:
                continue
            return []

        queries_raw = result.get("parallel_queries") or []
        queries: list[SubQuery] = []
        for q in queries_raw:
            action = q.get("action")
            if action not in ("query", "count", "group_count", "get_distinct"):
                continue
            queries.append(
                SubQuery(
                    action=action,
                    description=q.get("description", ""),
                    filters=q.get("filters") or {},
                    group_by=q.get("group_by"),
                    limit=q.get("limit"),
                )
            )

        logger.info(
            "Dynamic step %d generated %d queries (attempt %d)",
            step.step,
            len(queries),
            attempt + 1,
        )
        return queries

    return []


async def execute_plan(
    session: AsyncSession,
    plan: QueryPlan,
    user_question: str,
    client: openai.AsyncOpenAI,
) -> list[StepResult]:
    """Execute a QueryPlan step by step.

    For static steps, runs pre-defined parallel queries directly.
    For dynamic steps, asks the LLM to generate queries based on previous results
    and the original plan, then executes them in parallel.

    Returns a list of StepResult, one per step.
    """
    results: list[StepResult] = []

    for step in plan.steps:
        if step.mode == "static":
            queries = step.parallel_queries or []
        else:
            queries = await _generate_dynamic_queries(
                client,
                user_question,
                plan,
                step,
                results,
            )

        step_results = await _execute_parallel_queries(session, queries)
        results.append(StepResult(step=step, results=step_results))
        logger.info(
            "Step %d (%s) executed %d queries",
            step.step,
            step.mode,
            len(queries),
        )

    return results


def format_step_results(results: list[StepResult]) -> str:
    """Format execution results into natural-language context for the main AI."""
    parts: list[str] = []

    for sr in results:
        step = sr.step
        parts.append(f"【步骤{step.step}：{step.description}】")

        for res in sr.results:
            if "error" in res:
                desc = res.get("description", "")
                err = res["error"]
                parts.append(f"  [查询失败] {desc}: {err}")
                continue

            action = res.get("action")
            desc = res.get("description", "")

            if action == "query":
                total = res.get("total", 0)
                employees = res.get("employees", [])
                parts.append(f"  {desc}（共{total}人）：")
                for emp in employees[:20]:
                    info = f"- {emp.get('name')}（工号:{emp.get('employee_number')}）"
                    if emp.get("department"):
                        info += f"，部门:{emp.get('department')}"
                    if emp.get("position"):
                        info += f"，职位:{emp.get('position')}"
                    if emp.get("status"):
                        info += f"，状态:{emp.get('status')}"
                    if emp.get("education"):
                        info += f"，学历:{emp.get('education')}"
                    parts.append(f"    {info}")
                if len(employees) > 20:
                    parts.append(f"    ... 还有 {len(employees) - 20} 人")

            elif action == "count":
                count = res.get("count", 0)
                parts.append(f"  {desc}：{count}人")

            elif action == "group_count":
                groups = res.get("groups", [])
                group_by = res.get("group_by", "")
                parts.append(f"  {desc}（按{group_by}分组）：")
                total_count = 0
                for g in groups:
                    val = g.get("value", "未知")
                    cnt = g.get("count", 0)
                    total_count += cnt
                    parts.append(f"    - {val}：{cnt}人")
                parts.append(f"    共计：{total_count}人")

            elif action == "get_distinct":
                values = res.get("values", [])
                field = res.get("field", "")
                parts.append(f"  {desc}（{field}）：")
                parts.append(f"    {', '.join(values) if values else '无'}")

        parts.append("")

    return "\n".join(parts)
