"""Build Feishu Bitable query context for AI assistant.

This module allows the AI assistant to query Feishu Bitable (多维表格)
directly via natural language, with server-side filtering to avoid
loading large datasets into memory.
"""

import json
import logging
import re
from typing import Any

from app.core.config import get_settings
from app.platform.integrations.feishu.datasource import BitableDataSource

logger = logging.getLogger(__name__)

_settings = get_settings()


def _get_ai_query_tables() -> dict[str, dict[str, Any]]:
    """Parse FEISHU_AI_QUERY_TABLES config."""
    raw = _settings.FEISHU_AI_QUERY_TABLES
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Invalid FEISHU_AI_QUERY_TABLES JSON: %s", raw)
        return {}


def detect_feishu_table_intent(text: str) -> str | None:
    """Detect if user wants to query a Feishu Bitable table.

    Returns the matched table alias or None.
    """
    tables = _get_ai_query_tables()
    if not tables:
        return None

    # Priority 1: match configured table aliases
    for alias in tables:
        if alias in text:
            return alias

    # Priority 2: generic Feishu keywords
    if any(kw in text for kw in ("飞书", "多维表格", "bitable")):
        return next(iter(tables), None)

    return None


def _build_status_condition(text: str) -> str | None:
    """Extract status filter condition."""
    status_map = {
        "在职": "在职",
        "在岗": "在职",
        "离职": "离职",
        "休假": "休假",
        "停薪留职": "停薪留职",
        "实习": "实习",
        "试用期": "试用期",
        "停用": "停用",
        "注销": "注销",
    }
    for kw, value in status_map.items():
        if kw in text:
            return f'CurrentValue.[状态] = "{value}"'
    return None


def _build_department_condition(text: str) -> str | None:
    """Extract department filter condition."""
    m = re.search(
        r"([一-龥\w\-]{2,20}(?:部门|车间|科室|组|部|中心))", text
    )
    if m:
        return f'CurrentValue.[部门] = "{m.group(1)}"'
    return None


def _build_position_condition(text: str) -> str | None:
    """Extract position filter condition."""
    patterns = [
        r"(工程师|经理|主管|专员|操作员|文员|总监|助理|厂长|班长|组长)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return f'CurrentValue.[职位] = "{m.group(1)}"'
    return None


def _build_numeric_conditions(text: str, filterable_fields: list[str]) -> list[str]:
    """Extract numeric comparison conditions from text."""
    conditions: list[str] = []
    for field in filterable_fields:
        # Greater than
        m = re.search(
            rf"(?:{re.escape(field)}).*?(?:大于|超过|多于|≥|>=|>)",
            text,
        )
        if m:
            # Look for a number after the keyword
            num_m = re.search(r"[大于超过多于≥>=<≤]+\s*(\d+(?:\.\d+)?)", text)
            if num_m:
                conditions.append(
                    f'CurrentValue.[{field}] > "{num_m.group(1)}"'
                )
                continue

        # Less than
        m = re.search(
            rf"(?:{re.escape(field)}).*?(?:小于|少于|低于|≤|<=|<)",
            text,
        )
        if m:
            num_m = re.search(r"[小于少于低于≤<=]+\s*(\d+(?:\.\d+)?)", text)
            if num_m:
                conditions.append(
                    f'CurrentValue.[{field}] < "{num_m.group(1)}"'
                )
                continue

        # Equal to
        m = re.search(
            rf"(?:{re.escape(field)}).*?(?:等于|是)\s*(\d+(?:\.\d+)?)",
            text,
        )
        if m:
            conditions.append(f'CurrentValue.[{field}] = "{m.group(1)}"')
            continue

    return conditions


def extract_filter_conditions(
    text: str, filterable_fields: list[str]
) -> str | None:
    """Extract filter conditions from natural language and build Feishu filter_str.

    Args:
        text: User's natural language query.
        filterable_fields: List of field names that can be filtered.

    Returns:
        Feishu filter string or None if no conditions found.
    """
    conditions: list[str] = []

    # Status filter
    if "状态" in filterable_fields:
        cond = _build_status_condition(text)
        if cond:
            conditions.append(cond)

    # Department filter
    if "部门" in filterable_fields:
        cond = _build_department_condition(text)
        if cond:
            conditions.append(cond)

    # Position filter
    if "职位" in filterable_fields:
        cond = _build_position_condition(text)
        if cond:
            conditions.append(cond)

    # Numeric comparisons for all filterable fields
    conditions.extend(_build_numeric_conditions(text, filterable_fields))

    # Keyword contains (fallback for any field)
    for field in filterable_fields:
        if field in ("状态", "部门", "职位"):
            continue
        # If the field name itself appears followed by a value
        m = re.search(
            rf"{re.escape(field)}[是为:]\s*([^，。；\n]+)", text
        )
        if m:
            value = m.group(1).strip()
            if value:
                conditions.append(f'CurrentValue.[{field}] = "{value}"')
                break  # Only one fallback condition

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return " and ".join(conditions)


async def query_feishu_table(
    table_alias: str, filter_str: str | None
) -> list[dict[str, Any]]:
    """Query Feishu Bitable with optional filter.

    Args:
        table_alias: The configured table alias.
        filter_str: Feishu filter expression or None.

    Returns:
        List of raw Feishu records.
    """
    tables = _get_ai_query_tables()
    cfg = tables.get(table_alias)
    if not cfg:
        return []

    app_token = cfg.get("app_token") or _settings.FEISHU_BITABLE_APP_TOKEN
    table_id = cfg.get("table_id")
    if not table_id:
        logger.warning("No table_id configured for %s", table_alias)
        return []

    ds = BitableDataSource(app_token=app_token, table_id=table_id)
    max_rows = _settings.FEISHU_AI_QUERY_MAX_ROWS

    try:
        records = await ds.query(filter_str=filter_str, page_size=max_rows)
        logger.info(
            "Feishu query [%s] filter=%s returned %d records (max=%d)",
            table_alias,
            filter_str,
            len(records),
            max_rows,
        )
        return records
    except Exception:
        logger.exception("Feishu query failed for %s", table_alias)
        return []


def _format_field_value(value: Any) -> str:
    """Format a single field value for display."""
    if value is None:
        return ""
    if isinstance(value, list):
        # Handle multi-select, people, etc.
        parts = []
        for item in value:
            if isinstance(item, dict):
                # People field: {"name": "张三", "en_name": "..."}
                parts.append(str(item.get("name", item)))
            else:
                parts.append(str(item))
        return ", ".join(parts)
    if isinstance(value, dict):
        return str(value.get("text", value))
    return str(value)


def format_feishu_records(
    records: list[dict[str, Any]], table_alias: str
) -> str:
    """Format Feishu records as context text for AI prompt.

    Args:
        records: Raw Feishu records from API.
        table_alias: Table name for labeling.

    Returns:
        Formatted context string.
    """
    if not records:
        return f"【飞书多维表格查询结果 - {table_alias}】未找到匹配记录。"

    lines: list[str] = [
        f"【飞书多维表格查询结果 - {table_alias}】共 {len(records)} 条记录："
    ]

    for rec in records:
        fields = rec.get("fields", {})
        field_parts: list[str] = []
        for k, v in fields.items():
            formatted = _format_field_value(v)
            if formatted:
                field_parts.append(f"{k}：{formatted}")
        if field_parts:
            lines.append("- " + "，".join(field_parts))
        else:
            lines.append(f"- 记录 {rec.get('record_id', '')}")

    return "\n".join(lines)


async def build_feishu_context(user_text: str) -> str:
    """Build Feishu Bitable context for AI assistant.

    Returns formatted context string or empty string if no match.
    """
    table_alias = detect_feishu_table_intent(user_text)
    if not table_alias:
        return ""

    tables = _get_ai_query_tables()
    cfg = tables.get(table_alias, {})
    filterable_fields = cfg.get("filterable_fields", [])

    filter_str = extract_filter_conditions(user_text, filterable_fields)
    records = await query_feishu_table(table_alias, filter_str)

    return format_feishu_records(records, table_alias)
