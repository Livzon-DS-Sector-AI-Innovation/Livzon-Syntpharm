"""标准表 docx 与结果表 Excel 的三层标准交叉印证。

两份文件都能给出同一个项目的法定 / 内控 / 3σ 标准，但来源不同：

- 结果表：每列读**自己那一列**的第 3/4/5 行（列与列天然对齐）
- 标准表：每个项目一行，三层写在「说明」列里

一致就自动通过；不一致**不自行取舍**，交给使用者逐条判断；
只有一边有时按有值方采用并标注来源。

判定「一致」必须两级比较，否则会大量误报：`8.0%～11.0%` 与 `8.0～11.0％`
文本不同但语义相同，直接比字符串会误报二十多条。
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

from app.modules.quality.qc_report.constants import PLAIN_NUMBER_PATTERN
from app.modules.quality.qc_report.service.limits import (
    INACTIVE_LIMIT,
    KIND_INTERVAL,
    KIND_UPPER,
    LimitRange,
    is_empty_standard,
    parse_limit,
)

logger = logging.getLogger(__name__)

LAYERS: tuple[str, ...] = ("legal", "internal", "sigma")

LAYER_LABELS: dict[str, str] = {
    "legal": "法定标准",
    "internal": "企业内控标准",
    "sigma": "3σ 标准",
}

# 比对结论
STATUS_SAME = "same"  # 两边一致
STATUS_DIFF = "diff"  # 两边不一致，需人工判断
STATUS_ONLY_EXCEL = "only_excel"  # 标准表没有这一列
STATUS_ONLY_DOCX = "only_docx"  # 结果表没有这一列

# 冲突严重程度
SEVERITY_NUMERIC = "numeric"  # 数值范围不同，必须人工确认
SEVERITY_TEXT = "text"  # 只是文字表述不同，默认采用结果表

# 人工选择的取值来源
SOURCE_DOCX = "docx"
SOURCE_EXCEL = "excel"
SOURCE_NONE = "none"

# 归一化时统一成波浪号的分隔符（"至"、"～"、"~" 在标准里都表示区间）
_TILDE_VARIANTS = ("～", "至", "~")


def normalize_standard(text: str | None) -> str:
    """把标准原文归一成可比较的形式，只做写法层面的统一，不解读语义。"""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", str(text)).strip()
    if not normalized:
        return ""
    normalized = normalized.replace(" ", "").replace("\u3000", "")
    for variant in _TILDE_VARIANTS:
        normalized = normalized.replace(variant, "~")
    # 百分号位置各家写法不同（8.0%～11.0% / 8.0～11.0％），去掉不影响语义
    normalized = normalized.replace("%", "")
    return normalized


def is_single_value_text(text: str | None) -> bool:
    """是否是「只有一个数字」的标准（如吸收系数内控的 `517`）。

    这种标准构不成范围，无法判定超限；它属于可疑项，要作为冲突呈现给人看，
    而不是静默丢弃。
    """
    if not text:
        return False
    stripped = str(text).strip()
    if not stripped:
        return False
    return bool(PLAIN_NUMBER_PATTERN.fullmatch(stripped))


@dataclass(frozen=True)
class StandardComparison:
    """某一层标准的比对结论。"""

    status: str
    note: str | None = None
    severity: str | None = None

    @property
    def is_conflict(self) -> bool:
        return self.status == STATUS_DIFF


def _equivalent(left: LimitRange, right: LimitRange) -> bool:
    """两种写法是否表达同一个判定范围。"""
    if left == right:
        return left != INACTIVE_LIMIT
    # 「0.2～0.0」与「≤0.2%」：下界为 0 的区间等价于单边上限
    if left.kind == KIND_INTERVAL and right.kind == KIND_UPPER:
        return left.upper == right.upper and left.lower in (0.0, None)
    if right.kind == KIND_INTERVAL and left.kind == KIND_UPPER:
        return right.upper == left.upper and right.lower in (0.0, None)
    return False


_GRADE_TOKEN = re.compile(r"(?:O?Y|YG)\d+(?:\.\d+)?")


def _conflict_severity(excel_text: str | None, docx_text: str | None) -> str:
    """冲突分两档：数值不同是重点，文字表述不同只是写法差异。

    两边都能解析出判定范围且范围不相等 → numeric（必须人工确认）；
    一边是文字描述（`不得浓于1号浊度标准液`）或等级描述（`≤Y7/YG7/OY7`）→ text，
    这类差异不影响判定结果，默认采用结果表的值即可。
    """
    excel_limit = parse_limit(excel_text)
    docx_limit = parse_limit(docx_text)
    if excel_limit.is_active and docx_limit.is_active and excel_limit != docx_limit:
        return SEVERITY_NUMERIC
    return SEVERITY_TEXT


def _same_grade_tokens(left: str | None, right: str | None) -> bool:
    """等级型标准只比色号集合，不比书写顺序。

    「Y4.5/YG4.5/OY4.5～Y2.0/YG2.0/OY2.0」与反向书写是同一个区间。
    """
    left_tokens = sorted(_GRADE_TOKEN.findall(left or ""))
    right_tokens = sorted(_GRADE_TOKEN.findall(right or ""))
    return bool(left_tokens) and left_tokens == right_tokens


def compare_standard(excel_text: str | None, docx_text: str | None) -> StandardComparison:
    """比较同一层的两份标准。"""
    excel_empty = is_empty_standard(excel_text)
    docx_empty = is_empty_standard(docx_text)

    if excel_empty and docx_empty:
        return StandardComparison(STATUS_SAME)
    if excel_empty:
        return StandardComparison(STATUS_ONLY_DOCX)
    if docx_empty:
        # 标准表没写这一层、结果表写了：采用结果表的值。
        # 若该值只是一个数字（如吸收系数内控的 517），额外提示它构不成范围。
        note = "只有一个数值，构不成范围，不会作为判定依据" if is_single_value_text(excel_text) else None
        return StandardComparison(STATUS_ONLY_EXCEL, note)

    if normalize_standard(excel_text) == normalize_standard(docx_text):
        return StandardComparison(STATUS_SAME)

    # 写法不同但结构相同也算一致，如「8.0%～11.0%」与「8.0～11.0％」、
    # 「0.2～0.0」与「≤0.2%」（下界为 0 的区间本质就是上限约束）
    if _equivalent(parse_limit(excel_text), parse_limit(docx_text)):
        return StandardComparison(STATUS_SAME)

    # 等级型（Y7/YG7/OY7 这类色号）只比集合，顺序不同视为一致
    if _same_grade_tokens(excel_text, docx_text):
        return StandardComparison(STATUS_SAME)

    note = None
    if is_single_value_text(excel_text) != is_single_value_text(docx_text):
        note = "有一边只有一个数值，构不成范围，无法判定超限"
    return StandardComparison(STATUS_DIFF, note, _conflict_severity(excel_text, docx_text))


@dataclass(frozen=True)
class LayerComparison:
    """一列一层标准的比对明细，供预览与落库使用。"""

    column_index: int
    column_letter: str
    item_name: str
    layer: str
    excel_text: str | None
    docx_text: str | None
    status: str
    note: str | None = None
    severity: str | None = None

    @property
    def layer_label(self) -> str:
        return LAYER_LABELS.get(self.layer, self.layer)


def compare_item_layers(
    *,
    column_index: int,
    column_letter: str,
    item_name: str,
    excel_layers: dict[str, str | None],
    docx_layers: dict[str, str | None] | None,
) -> list[LayerComparison]:
    """比较一列的三层标准。`docx_layers=None` 表示标准表没有对应项目。"""
    results: list[LayerComparison] = []
    for layer in LAYERS:
        excel_text = excel_layers.get(layer)
        if docx_layers is None:
            status = STATUS_ONLY_EXCEL if not is_empty_standard(excel_text) else STATUS_SAME
            results.append(
                LayerComparison(
                    column_index=column_index,
                    column_letter=column_letter,
                    item_name=item_name,
                    layer=layer,
                    excel_text=excel_text,
                    docx_text=None,
                    status=status,
                    note="标准表未覆盖该列" if status == STATUS_ONLY_EXCEL else None,
                )
            )
            continue
        docx_text = docx_layers.get(layer)
        comparison = compare_standard(excel_text, docx_text)
        results.append(
            LayerComparison(
                column_index=column_index,
                column_letter=column_letter,
                item_name=item_name,
                layer=layer,
                excel_text=excel_text,
                docx_text=docx_text,
                status=comparison.status,
                note=comparison.note,
                severity=comparison.severity,
            )
        )
    return results


def resolve_layer(
    excel_text: str | None,
    docx_text: str | None,
    choice: str,
) -> tuple[str | None, str]:
    """按人工选择决定该层最终取值，返回 (最终文本, 来源标记)。"""
    if choice == SOURCE_DOCX:
        return docx_text, SOURCE_DOCX
    if choice == SOURCE_NONE:
        return None, SOURCE_NONE
    return excel_text, SOURCE_EXCEL


def default_source(status: str) -> str:
    """未发生冲突时，该层取值的来源标记。"""
    if status == STATUS_ONLY_DOCX:
        return SOURCE_DOCX
    return SOURCE_EXCEL


def summarize(
    comparisons: list[LayerComparison],
    *,
    total_columns: int,
    skipped_docx_items: list[str],
) -> dict[str, object]:
    """给前端的汇总：多少列一致、多少待确认、多少只有结果表有。"""
    columns_with_conflict = {c.column_index for c in comparisons if c.status == STATUS_DIFF}
    columns_only_excel = {c.column_index for c in comparisons if c.status == STATUS_ONLY_EXCEL} - columns_with_conflict
    return {
        "total_columns": total_columns,
        "same_count": total_columns - len(columns_with_conflict) - len(columns_only_excel),
        "conflict_count": len(columns_with_conflict),
        "only_excel_count": len(columns_only_excel),
        "skipped_standard_items": skipped_docx_items,
    }


__all__ = [
    "LAYERS",
    "LAYER_LABELS",
    "SOURCE_DOCX",
    "SOURCE_EXCEL",
    "SOURCE_NONE",
    "STATUS_DIFF",
    "STATUS_ONLY_DOCX",
    "STATUS_ONLY_EXCEL",
    "STATUS_SAME",
    "SEVERITY_NUMERIC",
    "SEVERITY_TEXT",
    "LayerComparison",
    "StandardComparison",
    "compare_item_layers",
    "compare_standard",
    "default_source",
    "is_single_value_text",
    "normalize_standard",
    "resolve_layer",
    "summarize",
]
