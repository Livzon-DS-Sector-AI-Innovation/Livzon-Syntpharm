"""AI query planner — Layer 1: generates an execution plan from user intent.

Uses a lightweight LLM (kimi-k2.5) to analyse natural-language questions and
produce a structured QueryPlan with up to 5 steps.  Each step can be static
(pre-defined parallel queries) or dynamic (queries generated at run-time based
on previous results).
"""

from __future__ import annotations

import json
import logging
from datetime import date

import openai

from app.platform.ai.schemas import PlanStep, QueryPlan, SubQuery

logger = logging.getLogger(__name__)

def _get_model() -> str:
    from app.core.config import get_settings
    return get_settings().AI_MODEL or "kimi-k2.5"

_PLANNER_SYSTEM_PROMPT = """你是工厂人事管理系统的「查询规划助手」。

## 任务
分析用户问题，生成一个最多5步的数据查询计划，用于获取回答该问题所需的全部数据。

## 可用查询操作
- query: 查询员工详细信息列表（如"有哪些人"、"名单"、"详细信息"）
- count: 统计人数（如"有多少人"、"共计几人"）
- group_count: 按某个字段分组统计（如"学历分布"、"各部门人数"、"按性别统计"）
- get_distinct: 获取某个字段的所有不重复值（如"有哪些部门"、"有哪些学历"）

## 可用过滤字段
department（部门）, team（班组）, position（职位）, status（状态）, gender（性别）,
education（学历）, political_status（政治面貌）, marital_status（婚姻状况）,
status_category（统计类别）,
age_min（最小年龄）, age_max（最大年龄）,
birth_year_min（出生年份下限）, birth_year_max（出生年份上限）,
hire_date_after（入职日期下限）, hire_date_before（入职日期上限）,
factory_entry_date_after（进厂日期下限）, factory_entry_date_before（进厂日期上限）,
work_start_date_after（参加工作日期下限）, work_start_date_before（参加工作日期上限）

## 计划规则（关键）
1. 能一步直接回答的问题 → 1 步 static，parallel_queries 直接包含所需查询
2. 需要先获取某些值再基于这些值查询 → 先 static 获取值，再 dynamic 基于值生成后续查询
3. static 步骤必须填充 parallel_queries（可放多条，这些查询会并行执行）
4. dynamic 步骤只写 description（意图），具体查询由执行器在运行时生成
5. 每步的 parallel_queries 可以包含多条查询，这些查询在该步骤内并行执行
6. 如果问题不需要查数据（如"你好"、"系统怎么用"），返回 needs_data=false
7. 默认排除待审批员工：如果用户没有明确提到"待审批"，不要添加 status="待审批"
8. position 字段使用模糊匹配，提取最核心的职位关键词即可

## 日期处理规则
- "2020年后入职" → hire_date_after="2020-01-01"
- "2020年前入职" → hire_date_before="2019-12-31"
- "最近1年入职" → hire_date_after=今天减1年
- "最近3个月入职" → hire_date_after=今天减3个月
- "1990年后出生" → birth_year_min=1990
- "30岁以下" → age_max=30
- "30岁以上" → age_min=30
- "30-40岁" → age_min=30, age_max=40

## 判断查询类型
- "分布/占比/各…多少/按…统计/分组" → group_count
- "有哪些类型/类别/选项/种类" → get_distinct
- "名单/详细信息/是谁/情况如何/列表" → query
- "有多少/几人/共计/统计人数" → count

## 输出格式（极其重要）
1. 你必须且只能输出一个 JSON 对象
2. 不要加任何其他文字、markdown 代码块标记（如 ```json）、或解释
3. 确保 JSON 完整、合法，不要截断
4. 不要输出任何中文字段名或值之外的内容

格式如下：
{
  "needs_data": true,
  "steps": [
    {
      "step": 1,
      "mode": "static",
      "description": "查询所有部门名称",
      "parallel_queries": [
        {"action": "get_distinct", "description": "获取所有部门",
         "group_by": "department", "filters": {}}
      ],
      "reasoning": "需要知道有哪些部门才能分别统计"
    },
    {
      "step": 2,
      "mode": "dynamic",
      "description": "对每个部门查询在职员工的学历分布",
      "reasoning": "基于步骤1获取的部门列表，分别统计每个部门的学历分布"
    }
  ],
  "reasoning": "用户想知道每个部门的学历分布，需要先知道有哪些部门，再分别统计"
}

如果不需要查询数据：
{
  "needs_data": false,
  "reasoning": "说明为什么不需要查询"
}

## 当前日期
{today}
"""


def _build_planner_prompt(user_text: str) -> tuple[str, str]:
    """Build system and user prompts for plan generation."""
    today = date.today().isoformat()
    system = _PLANNER_SYSTEM_PROMPT.replace("{today}", today)
    return system, user_text


def _parse_sub_query(raw: dict) -> SubQuery | None:
    """Parse a raw sub-query dict into a SubQuery model."""
    action = raw.get("action")
    if action not in ("query", "count", "group_count", "get_distinct"):
        return None
    return SubQuery(
        action=action,
        description=raw.get("description", ""),
        filters=raw.get("filters") or {},
        group_by=raw.get("group_by"),
        limit=raw.get("limit"),
    )


def _parse_plan_step(raw: dict) -> PlanStep | None:
    """Parse a raw step dict into a PlanStep model."""
    mode = raw.get("mode")
    if mode not in ("static", "dynamic"):
        mode = "static"

    parallel_queries = None
    if mode == "static" and raw.get("parallel_queries"):
        parsed_queries = []
        for q in raw["parallel_queries"]:
            sq = _parse_sub_query(q)
            if sq:
                parsed_queries.append(sq)
        parallel_queries = parsed_queries if parsed_queries else None

    return PlanStep(
        step=raw.get("step", 1),
        mode=mode,
        description=raw.get("description", ""),
        parallel_queries=parallel_queries,
        reasoning=raw.get("reasoning", ""),
    )


def _parse_plan(raw: dict) -> QueryPlan | None:
    """Parse LLM JSON output into a QueryPlan model."""
    if not raw.get("needs_data"):
        return QueryPlan(needs_data=False, reasoning=raw.get("reasoning", ""))

    steps_raw = raw.get("steps") or []
    steps = []
    for s in steps_raw:
        step = _parse_plan_step(s)
        if step:
            steps.append(step)

    if not steps:
        return None

    return QueryPlan(
        needs_data=True,
        steps=steps,
        reasoning=raw.get("reasoning", ""),
    )


async def generate_plan(
    client: openai.AsyncOpenAI,
    user_text: str,
) -> QueryPlan | None:
    """Generate a QueryPlan from user natural-language text.

    Returns None if the text does not require data, or if the LLM fails.
    Retries up to 2 times on empty or invalid JSON responses.
    """
    system_prompt, user_prompt = _build_planner_prompt(user_text)

    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=_get_model(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=1.0,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.warning("Planner LLM call failed (attempt %d): %s", attempt + 1, exc)
            if attempt < 2:
                continue
            return None

        raw = response.choices[0].message.content
        if not raw:
            logger.warning("Planner returned empty content (attempt %d)", attempt + 1)
            if attempt < 2:
                continue
            return None

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "Planner returned invalid JSON (attempt %d): %s\nRaw: %s",
                attempt + 1,
                exc,
                raw[:500],
            )
            if attempt < 2:
                continue
            return None

        plan = _parse_plan(result)
        if plan:
            logger.info(
                "Plan generated (attempt %d): %d steps, reasoning=%s",
                attempt + 1,
                len(plan.steps),
                plan.reasoning,
            )
            return plan

    logger.debug("Planner decided no plan needed or parsing failed after retries")
    return None
