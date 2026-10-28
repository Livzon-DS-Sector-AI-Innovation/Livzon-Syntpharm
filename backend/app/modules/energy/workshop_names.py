"""能源车间名称归一化与别名解析。

交叉表导入、多维表格同步、Excel 导入三条建车间路径共用这一份规则：
只改其中一条路径，别处仍会按字面名称把别名车间重新建出来。
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

# 多维表格内维护车间映射时使用的表名
MAPPING_TABLE_NAME = "车间映射"

# 同一部门在 水/电/汽 三个 section 里的同义写法 → 规范名称。
# 这些是业务事实（QC 与 质量控制部 无字面重叠），正则推不出来，只能显式登记。
# 未登记会导致同一部门被建成两个车间，月度记录的车间筛选因此只能看到单一能源类型。
# 多维表格存在「车间映射」表时以表为准，本常量作为兜底。详见 docs/energy-bitable-field-mapping.md
#
# 命中多个别名指向同一规范实体时，列表顺序有意义：先出现的那条负责「改名」建出规范实体，
# 后面的才能走「合并」。合并脚本直接复用本顺序。
WORKSHOP_ALIASES: dict[str, str] = {
    "QC": "质量控制部",
    "炊事班": "饭堂",
    "生活办公": "办公楼",
    "环保中心(含RTO)": "环保中心",
    "废水站": "环保中心",
    "303、106": "303、106车间",
    # 2024/2025 的历史月份表里 303 写成 303车间，与 303、106车间 是同一个车间
    "303车间": "303、106车间",
    # RTO 是一台独立的部门设备，电和气分开两处记录，必须归到同一个车间实体
    "RTO用电": "RTO",
    "RTO(天然气)": "RTO",
}


def normalize_workshop_name(name: str) -> str:
    """统一全角/半角与首尾空白，纯数字名称补「车间」后缀。"""
    normalized = unicodedata.normalize("NFKC", name).strip()
    if re.fullmatch(r"\d+", normalized):
        normalized += "车间"
    return normalized


def normalize_alias_map(alias_map: dict[str, str]) -> dict[str, str]:
    return {
        normalize_workshop_name(alias): normalize_workshop_name(canonical) for alias, canonical in alias_map.items()
    }


NORMALIZED_WORKSHOP_ALIASES = normalize_alias_map(WORKSHOP_ALIASES)


def resolve_workshop_name(name: str, alias_map: dict[str, str]) -> str:
    """归一化并套用别名，得到规范车间名。"""
    normalized = normalize_workshop_name(name)
    return alias_map.get(normalized, normalized)


async def load_workshop_alias_map(
    list_tables: Callable[[], Awaitable[list[dict[str, Any]]]],
    list_records: Callable[[str], Awaitable[list[dict[str, Any]]]],
) -> dict[str, str]:
    """读取「车间映射」表的别名列，缺表时回退内置常量。"""
    alias_map = dict(NORMALIZED_WORKSHOP_ALIASES)

    try:
        tables = await list_tables()
    except Exception:
        logger.warning("读取多维表格数据表失败，使用内置车间别名 %d 条", len(alias_map), exc_info=True)
        return alias_map

    table_id = next((t.get("table_id") for t in tables if t.get("name") == MAPPING_TABLE_NAME), None)
    if not table_id:
        logger.warning("未找到「%s」表，使用内置车间别名 %d 条", MAPPING_TABLE_NAME, len(alias_map))
        return alias_map

    try:
        records = await list_records(table_id)
    except Exception:
        logger.warning(
            "读取「%s」表记录失败，使用内置车间别名 %d 条", MAPPING_TABLE_NAME, len(alias_map), exc_info=True
        )
        return alias_map

    for record in records:
        fields = record.get("fields", {})
        canonical = normalize_workshop_name(str(fields.get("名称") or fields.get("name") or ""))
        if not canonical:
            continue
        raw_alias = str(fields.get("别名") or fields.get("alias") or "")
        for alias in re.split(r"[、,，]", raw_alias):
            alias = normalize_workshop_name(alias)
            if alias:
                alias_map[alias] = canonical

    logger.info("从「%s」表加载车间别名 %d 条", MAPPING_TABLE_NAME, len(alias_map))
    return alias_map
