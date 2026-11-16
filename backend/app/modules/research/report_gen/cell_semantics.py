"""单元格语义层：表头 → 期望内容 → 写入校验。

为什么单独成一层：表头语义（「技术部意见」「研发投入」「CAS号」）既决定模型该写什么，
也决定写入时该拒绝什么。若两处各判一套，就会出现「清单说是意见栏、校验却按普通文本放行」
这种自相矛盾。这里只放纯函数：不读 docx、不碰数据库、不调模型，便于单测与复用。

实际踩到的两类错填都靠这一层兜住：

- 把「其他名称 / 英文名 / 化学名称 / CAS号」这些**字段名**写进意见栏；
- 把「米诺地尔 / Minoxidil / 分子量」按顺序塞进成本表的数值列。
"""

from __future__ import annotations

import re

EXPECT_TEXT = "text"
EXPECT_NUMBER = "number"
EXPECT_CAS = "cas"
EXPECT_FORMULA = "formula"
EXPECT_OPINION = "opinion"

# 评审/审批类栏位：只接受人话意见，不接受字段名或型号
_OPINION_WORDS = ("意见", "审核", "批准", "会签", "签署", "签名")

# 数值类栏位：值里必须出现数字（允许「约 300 万元」「2-3 年」「18 个月」这类写法）。
# 刻意不收「批量/规格」：这两列经常填「中试规模」这种没有数字的描述，误伤大于收益。
_NUMBER_WORDS = (
    "成本",
    "价格",
    "金额",
    "费用",
    "投入",
    "数量",
    "周期",
    "产能",
    "人力",
    "人数",
    "比例",
    "纯度",
    "收率",
    "含量",
    "分子量",
)

# 常见的「字段名」：它们出现在普通格子里就是错位，只能写进对应字段自己的格子
FIELD_LABELS = frozenset(
    {
        "药品名称",
        "通用名称",
        "通用名",
        "其他名称",
        "别名",
        "英文名",
        "英文名称",
        "化学名称",
        "化学名",
        "中文名称",
        "CAS号",
        "CAS 号",
        "CAS",
        "分子式",
        "分子量",
        "性状",
        "外观",
        "规格",
        "剂型",
        "适应症",
        "用法用量",
        "贮藏",
        "有效期",
        "批准文号",
        "上市许可持有人",
        "原研企业",
        "商品名",
    }
)

_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
# 分子式：元素符号（首字母大写，可选一个小写）后面跟可选下标，至少两段，如 C9H15N5O
_FORMULA_RE = re.compile(r"^(?:[A-Z][a-z]?\d*){2,}$")
_DIGIT_RE = re.compile(r"\d")
_CJK_RE = re.compile(r"[\u4e00-\u9fa5]")
# 「其他名称」「英文名」「CAS号」这类短标签：长度短 + 以字段词收尾
_BARE_LABEL_TAIL_RE = re.compile(
    r"^[\u4e00-\u9fa5A-Za-z]{0,6}(?:名称|英文名|中文名|化学名|通用名|CAS\s?号|分子式|分子量|别名)$"
)


def _normalize(value: str | None) -> str:
    return " ".join((value or "").split())


def _hints(row_hint: str, column_hint: str) -> str:
    return f"{row_hint} {column_hint}".strip()


def expect_of(row_hint: str, column_hint: str = "") -> str:
    """由行标题/列路径推断这一格期望什么内容。

    顺序很重要：意见栏优先（「审核意见」里也含「意见」，不能被后面的数值词抢走），
    然后是 CAS、分子式这两类有强格式的，最后才是数值列。
    """
    hints = _hints(row_hint, column_hint)
    if any(word in hints for word in _OPINION_WORDS):
        return EXPECT_OPINION
    if "cas" in hints.lower():
        return EXPECT_CAS
    if "分子式" in hints:
        return EXPECT_FORMULA
    if any(word in hints for word in _NUMBER_WORDS):
        return EXPECT_NUMBER
    return EXPECT_TEXT


def is_bare_field_label(value: str | None) -> bool:
    """值本身就是一个字段名（「其他名称」「CAS号」），而不是这一格的内容。"""
    text = _normalize(value)
    if not text or len(text) > 12:
        return False
    return text in FIELD_LABELS or bool(_BARE_LABEL_TAIL_RE.match(text))


def _hint_mentions_label(hints: str, value: str) -> bool:
    """字段名写进「它自己的格子」是正常的（如 药品名称 行的值格）。"""
    text = _normalize(value)
    if text and text in hints:
        return True
    return any(label in hints and label in text for label in FIELD_LABELS)


def validate_cell_value(
    *,
    value: str | None,
    expect: str,
    row_hint: str = "",
    column_hint: str = "",
) -> str | None:
    """按目标格语义校验要写入的值；返回拒绝原因，``None`` 表示通过。

    取向是「宁拒勿错」：拿不准就拒绝，位置会显示成待填写，由人来补，
    而不是把错的字写进受控文档。
    """
    text = _normalize(value)
    if not text:
        return "内容不能为空"

    hints = _hints(row_hint, column_hint)

    # 字段名只能写进它自己的格子：写别处就是错位（本次事故的主要形态）
    if is_bare_field_label(text) and not _hint_mentions_label(hints, text):
        target = f"「{row_hint or column_hint}」" if (row_hint or column_hint) else "这一格"
        return f"{target}要写的是内容，不是字段名（{text}）；请按这一格的含义填写或留空"

    if expect == EXPECT_OPINION:
        if not _CJK_RE.search(text):
            return "这是意见栏，要写中文评审意见，不能写名称、编号或型号"
        return None

    if expect == EXPECT_CAS:
        if not _CAS_RE.match(text):
            return "这一列是 CAS 号，只能写「38304-91-5」这种格式"
        return None

    if expect == EXPECT_FORMULA:
        if not _FORMULA_RE.match(text):
            return "这一列是分子式，只能写「C9H15N5O」这种元素式"
        return None

    if expect == EXPECT_NUMBER:
        if _CAS_RE.match(text):
            return "这一列是数值（成本/周期/数量之类），不能写 CAS 号"
        if _FORMULA_RE.match(text):
            return "这一列是数值（成本/周期/数量之类），不能写分子式"
        if not _DIGIT_RE.search(text):
            return "这一列是数值（成本/周期/数量之类），值里必须有数字；拿不到数据就留空"
        return None

    return None


def expect_label(expect: str) -> str:
    """期望类型的中文说法，用于拒绝原因与清单展示。"""
    return {
        EXPECT_NUMBER: "数值",
        EXPECT_CAS: "CAS 号",
        EXPECT_FORMULA: "分子式",
        EXPECT_OPINION: "评审意见",
    }.get(expect, "文本")


__all__ = [
    "EXPECT_CAS",
    "EXPECT_FORMULA",
    "EXPECT_NUMBER",
    "EXPECT_OPINION",
    "EXPECT_TEXT",
    "FIELD_LABELS",
    "expect_label",
    "expect_of",
    "is_bare_field_label",
    "validate_cell_value",
]
