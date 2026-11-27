"""标准表项目 ↔ 结果表列 的桥接。

两份文件的项目名写法经常不同（同一项目在两边叫法不一致），
所以先做名称归一化自动匹配，匹配不上的交给人工点一次对应关系。

这里不内置任何「某个项目名固定对应某一列」的规则：
自动匹配只依据名称归一化结果，最终对应关系由使用者指定并按品种保存。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.modules.quality.qc_report.service.xlsx_parser import ColumnHeader

logger = logging.getLogger(__name__)

_PREFIXES = ("有关物质-", "有关物质－", "残留溶媒-", "残留溶媒－", "残留溶剂-")
_BRACKET = re.compile(r"\([^)]*\)")
_NOISE = ("【", "】", "[", "]", "　", " ")


@dataclass
class AutoMatch:
    """自动匹配成功的一项。"""

    item_name: str
    column_index: int
    column_name: str
    match_kind: str  # saved / exact / contain


@dataclass
class CandidateColumn:
    """待人工指定时的候选列。用列字母区分同名列。"""

    letter: str
    name: str


@dataclass
class PendingMatch:
    """需要人工指定对应哪一列的项目。"""

    item_name: str
    candidates: list[CandidateColumn] = field(default_factory=list)


@dataclass
class BridgeResult:
    """桥接结果。"""

    auto: list[AutoMatch]
    pending: list[PendingMatch]
    extra_columns: list[ColumnHeader]


def normalize_name(name: str) -> str:
    """归一化项目名：去前缀、去括号内容、去装饰符号。"""
    text = (name or "").replace("（", "(").replace("）", ")")
    for prefix in _PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    text = _BRACKET.sub("", text)
    for noise in _NOISE:
        text = text.replace(noise, "")
    return text.strip()


def bridge_items(
    item_names: list[str],
    columns: list[ColumnHeader],
    existing_mapping: dict[str, str] | None = None,
) -> BridgeResult:
    """把标准表项目名对到结果表的列上。

    Args:
        item_names: 标准表里的项目名（按顺序）
        columns: 结果表的列（已排除批号列）
        existing_mapping: 项目名 -> 列字母或列名。命中则直接复用。
            优先按列字母匹配：结果表里存在同名列（如可见异物初检的 4 个子列），
            按列名会指错，按列字母才唯一。
    """
    existing_mapping = existing_mapping or {}
    by_letter = {column.letter: column for column in columns}
    by_name = {column.name: column for column in columns}
    used_columns: set[int] = set()
    auto: list[AutoMatch] = []
    pending: list[PendingMatch] = []
    remaining: list[str] = []

    # 0) 复用历史映射或本次人工指定的对应关系
    for item_name in item_names:
        mapped = existing_mapping.get(item_name)
        column = None
        if mapped:
            column = by_letter.get(mapped) or by_name.get(mapped)
        if column is not None and column.index not in used_columns:
            used_columns.add(column.index)
            auto.append(
                AutoMatch(
                    item_name=item_name,
                    column_index=column.index,
                    column_name=column.name,
                    match_kind="saved",
                )
            )
        else:
            remaining.append(item_name)

    # 1) 精确匹配
    normalized_columns = [(column, normalize_name(column.name)) for column in columns]
    still_remaining: list[str] = []
    for item_name in remaining:
        key = normalize_name(item_name)
        hit = next(
            (column for column, norm in normalized_columns if norm == key and column.index not in used_columns),
            None,
        )
        if hit is not None:
            used_columns.add(hit.index)
            auto.append(
                AutoMatch(
                    item_name=item_name,
                    column_index=hit.index,
                    column_name=hit.name,
                    match_kind="exact",
                )
            )
        else:
            still_remaining.append(item_name)

    # 2) 包含匹配（双向）
    for item_name in still_remaining:
        key = normalize_name(item_name)
        hit = None
        if key:
            for column, norm in normalized_columns:
                if column.index in used_columns or not norm:
                    continue
                if key in norm or norm in key:
                    hit = column
                    break
        if hit is not None:
            used_columns.add(hit.index)
            auto.append(
                AutoMatch(
                    item_name=item_name,
                    column_index=hit.index,
                    column_name=hit.name,
                    match_kind="contain",
                )
            )
        else:
            pending.append(
                PendingMatch(
                    item_name=item_name,
                    candidates=[
                        CandidateColumn(letter=column.letter, name=column.name)
                        for column in columns
                        if column.index not in used_columns
                    ],
                )
            )

    extra = [column for column in columns if column.index not in used_columns]
    logger.info(
        "qc_report bridge done",
        extra={
            "item_count": len(item_names),
            "auto_matched": len(auto),
            "pending": len(pending),
            "extra_columns": len(extra),
        },
    )
    return BridgeResult(auto=auto, pending=pending, extra_columns=extra)


__all__ = [
    "AutoMatch",
    "BridgeResult",
    "CandidateColumn",
    "PendingMatch",
    "bridge_items",
    "normalize_name",
]
