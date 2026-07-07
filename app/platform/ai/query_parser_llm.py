"""LLM-based natural-language query parser for HR employee queries.

Uses a lightweight Moonshot model (moonshot-v1-8k-vision-preview) to extract
structured filter conditions from arbitrary Chinese user text.

Flow:
    user text -> LLM intent parser -> JSON criteria -> database query
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai

from app.platform.ai.query_parser import EmployeeQueryCriteria

logger = logging.getLogger(__name__)

def _get_model() -> str:
    from app.core.config import get_settings
    return get_settings().AI_MODEL or "kimi-k2.5"

_INTENT_SYSTEM_PROMPT = """你是工厂人事管理系统的「意图识别助手」。你的唯一任务是从用户的自然语言消息中提取数据库查询条件。

## 可用字段
你可以从用户消息中提取以下字段（只提取消息中明确提到的）：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| department | string | 部门/车间/科室/组/部/中心名称 | "生产部"、"研发中心" |
| team | string | 班组 | "一班"、"甲班" |
| position | string | 职位关键词（支持模糊） | "工程师"会匹配"研发工程师"、"设备工程师" |
| status | string | 员工状态 | "在职"、"离职"、"试用期"、"待审批" |
| gender | string | 性别 | "男"、"女" |
| education | string | 学历 | "高中"、"中专"、"大专"、"本科"、"研究生"、"硕士"、"博士" |
| political_status | string | 政治面貌 | "党员"、"群众"、"团员"、"预备党员" |
| marital_status | string | 婚姻状况 | "已婚"、"未婚"、"离异"、"丧偶" |
| age_min | integer | 最小年龄 | 30 表示30岁以上 |
| age_max | integer | 最大年龄 | 30 表示30岁以下 |
| birth_year_min | integer | 出生年份下限 | 1990 表示1990年后出生 |
| birth_year_max | integer | 出生年份上限 | 1990 表示1990年前出生 |
| hire_date_after | string | 入职日期下限(YYYY-MM-DD) | "2020-01-01"表示2020年后入职 |
| hire_date_before | string | 入职日期上限(YYYY-MM-DD) | "2020-12-31"表示2020年前入职 |
| factory_entry_date_after | string | 进厂日期下限 | "2020-01-01" |
| factory_entry_date_before | string | 进厂日期上限 | "2020-12-31" |
| work_start_date_after | string | 参加工作日期下限 | "2015-01-01" |
| work_start_date_before | string | 参加工作日期上限 | "2015-12-31" |

## 查询类型判断
- "list": 用户想看列表/名单/详细信息（如"有哪些人"、"名单"、"是谁"、"情况如何"）
- "count": 用户只想知道数量（如"有多少"、"几人"、"人数"、"统计"、"共计"）

## 日期处理规则
- "2020年后入职" -> hire_date_after = "2020-01-01"
- "2020年前入职" -> hire_date_before = "2019-12-31"
- "最近1年入职" -> hire_date_after = 今天减去1年（用当前日期）
- "最近3个月入职" -> hire_date_after = 今天减去3个月
- "1990年后出生" -> birth_year_min = 1990
- "30岁以下" -> age_max = 30
- "30岁以上" -> age_min = 30
- "30-40岁" -> age_min = 30, age_max = 40

## 重要规则
1. 只提取用户消息中**明确提到**的条件，不要猜测未提及的字段。
2. 如果用户问的是通用问题（如"你好"、"谢谢"、"今天天气如何"），返回 needs_data = false。
3. 如果用户问的是人事相关问题但不需要查数据库（如"怎么添加员工"、"系统怎么用"），返回 needs_data = false。
4. 组合条件：如果用户提到多个条件（如"生产部在职的工程师"），全部放入 filters。
5. position 字段使用模糊匹配，提取最核心的职位关键词即可（如"研发工程师"提取"工程师"，"生产部经理"提取"经理"）。
6. 默认排除待审批员工：如果用户没有明确提到"待审批"，不要添加 status="待审批"。
7. 当前日期：{today}。

## 输出格式
你必须且只能输出一个 JSON 对象，不要加任何其他文字、markdown 代码块标记或解释。

格式如下：
{{
  "needs_data": true,
  "query_type": "list" 或 "count",
  "filters": {{
    // 只放提取到的字段
  }},
  "reasoning": "简要说明提取逻辑"
}}

如果不需要查询数据：
{{
  "needs_data": false,
  "reasoning": "说明为什么不需要查询"
}}
"""


def _build_intent_prompt(user_text: str) -> tuple[str, str]:
    """Build the system and user prompts for intent extraction."""
    from datetime import date

    today = date.today().isoformat()
    system = _INTENT_SYSTEM_PROMPT.format(today=today)
    return system, user_text


async def parse_with_llm(
    client: openai.AsyncOpenAI,
    user_text: str,
) -> EmployeeQueryCriteria | None:
    """Use a lightweight LLM to parse user intent into structured query criteria.

    Returns None if the text does not appear to be an employee query,
    or if the LLM fails to produce valid output.
    """
    system_prompt, user_prompt = _build_intent_prompt(user_text)

    try:
        response = await client.chat.completions.create(
            model=_get_model(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=1.0,
            max_tokens=512,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        logger.warning("LLM intent parsing failed: %s", exc)
        return None

    raw = response.choices[0].message.content
    if not raw:
        logger.warning("LLM intent parsing returned empty content")
        return None

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("LLM intent parsing returned invalid JSON: %s", exc)
        return None

    if not result.get("needs_data"):
        logger.debug("LLM decided no data needed: %s", result.get("reasoning"))
        return None

    filters = result.get("filters") or {}
    if not filters:
        logger.debug("LLM returned no filters")
        return None

    criteria = EmployeeQueryCriteria()
    criteria.query_type = result.get("query_type", "list")
    criteria.filters = _normalize_filters(filters)
    return criteria


def _normalize_filters(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate filter values from LLM output."""
    filters: dict[str, Any] = {}

    # String fields
    for key in (
        "department",
        "team",
        "position",
        "status",
        "gender",
        "education",
        "political_status",
        "marital_status",
    ):
        value = raw.get(key)
        if value is not None and isinstance(value, str) and value.strip():
            filters[key] = value.strip()

    # Integer fields
    for key in ("age_min", "age_max", "birth_year_min", "birth_year_max"):
        value = raw.get(key)
        if value is not None:
            try:
                filters[key] = int(value)
            except (ValueError, TypeError):
                pass

    # Date fields (validate format and convert to date objects)
    for key in (
        "hire_date_after",
        "hire_date_before",
        "factory_entry_date_after",
        "factory_entry_date_before",
        "work_start_date_after",
        "work_start_date_before",
    ):
        value = raw.get(key)
        if value is not None and isinstance(value, str):
            # Basic YYYY-MM-DD validation
            if len(value) == 10 and value[4] == "-" and value[7] == "-":
                from datetime import date as dt

                try:
                    filters[key] = dt.fromisoformat(value)
                except ValueError:
                    pass

    return filters
