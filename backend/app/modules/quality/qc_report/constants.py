"""质量检验台账常量：判定等级、优先级、项目类型与限值解析规则。"""

from __future__ import annotations

import re

# ── 判定等级 ────────────────────────────────────────────────
LEVEL_OOS = "oos"  # 超法定
LEVEL_INTERNAL = "internal"  # 超企业内控
LEVEL_TREND = "trend"  # 超 3σ
LEVEL_NORMAL = "normal"  # 正常
LEVEL_SKIP = "skip"  # 等级型，不判定
LEVEL_PENDING = "pending"  # 待检

ALL_LEVELS = (
    LEVEL_OOS,
    LEVEL_INTERNAL,
    LEVEL_TREND,
    LEVEL_NORMAL,
    LEVEL_SKIP,
    LEVEL_PENDING,
)

LEVEL_PRIORITY: dict[str, int] = {
    LEVEL_OOS: 4,
    LEVEL_INTERNAL: 3,
    LEVEL_TREND: 2,
    LEVEL_NORMAL: 1,
    LEVEL_SKIP: 0,
    LEVEL_PENDING: -1,
}

LEVEL_LABELS: dict[str, str] = {
    LEVEL_OOS: "超法定",
    LEVEL_INTERNAL: "超内控",
    LEVEL_TREND: "超趋势",
    LEVEL_NORMAL: "正常",
    LEVEL_SKIP: "仅记录",
    LEVEL_PENDING: "待检",
}

# 参与行级汇总的等级（待检与仅记录不计入）
AGGREGATED_LEVELS = (LEVEL_OOS, LEVEL_INTERNAL, LEVEL_TREND, LEVEL_NORMAL)

# ── 项目类型 ────────────────────────────────────────────────
VALUE_TYPE_QUANT = "quant"  # 数值型，参与三层判定
VALUE_TYPE_QUAL = "qual"  # 文字型，按否定词判定
VALUE_TYPE_GRADE = "grade"  # 等级型，仅记录

# 文字型项目出现以下表述即判为超法定
NEGATIVE_KEYWORDS = ("不符合", "不呈", "不合格", "未通过")

# ── 品种物料分类 ────────────────────────────────────────────
CATEGORY_RAW = "raw"
CATEGORY_INTERMEDIATE = "intermediate"
CATEGORY_FINISHED = "finished"

CATEGORY_LABELS: dict[str, str] = {
    CATEGORY_RAW: "原料",
    CATEGORY_INTERMEDIATE: "中间体",
    CATEGORY_FINISHED: "成品",
}

# 导入来源
SOURCE_IMPORT = "import"
SOURCE_MANUAL = "manual"

# 标准表 docx 中需要跳过的基础字段行（不是检验项目）
STANDARD_TABLE_SKIP_FIELDS = ("品名", "批号", "生产日期")

# 结果表中承载批号的列
RESULT_BATCH_COLUMN_HEADERS = ("批号", "batch_no")

# ── 限值文本解析 ────────────────────────────────────────────
# 全角/半角混用的区间与比较符
_TILDE = r"[~～\-－—]"
_NUM = r"-?\d+(?:\.\d+)?"
_CMP_PREFIX = {"<=": "upper", "＜=": "upper", "≤": "upper", "<": "upper", "＜": "upper"}
_CMP_SUFFIX = {">=": "lower", "＞=": "lower", "≥": "lower", ">": "lower", "＞": "lower"}

# 区间中间可能夹着单位符号，如「-153°～-170°」
INTERVAL_PATTERN = re.compile(rf"({_NUM})\s*[°º℃%％]?\s*{_TILDE}\s*({_NUM})")
UPPER_PATTERN = re.compile(rf"(?:≤|＜|<|不超过|不得过|不得大于|应不得过)\s*({_NUM})")
LOWER_PATTERN = re.compile(rf"(?:≥|＞|>|不低于|不得少于)\s*({_NUM})")
PLAIN_NUMBER_PATTERN = re.compile(rf"^{_NUM}$")

# 等级型特征：Y7/YG7/OY7 之类色号，或"不得深于 N"
GRADE_PATTERN = re.compile(r"[Yy]{1,2}\d|不得深于|不得浅于")
# 文字型特征
QUAL_PATTERN = re.compile(r"符合规定|呈正反应|不得浓于|不得浅于|应符合|应呈|符合要求")

# 中文数字（用于"百万分之二十"这类表述）
_CN_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
CN_FRACTION_PATTERN = re.compile(r"([百万千]+)分之([零一二三四五六七八九十百]+)")
CN_FRACTION_SCALE = {"百万": 1.0, "十万": 10.0, "万": 100.0, "千": 1000.0}

# 无标准的表示
# 「一致」表示沿用法定标准，本身不构成独立阈值；放进这里可让
# 「内控=一致」与「内控未填」在判定和交叉印证里得到同样的处理。
NO_STANDARD_TEXTS = ("", "/", "／", "-", "—", "未作规定", "无", "一致")

__all__ = [
    "LEVEL_OOS",
    "LEVEL_INTERNAL",
    "LEVEL_TREND",
    "LEVEL_NORMAL",
    "LEVEL_SKIP",
    "LEVEL_PENDING",
    "ALL_LEVELS",
    "LEVEL_PRIORITY",
    "LEVEL_LABELS",
    "AGGREGATED_LEVELS",
    "VALUE_TYPE_QUANT",
    "VALUE_TYPE_QUAL",
    "VALUE_TYPE_GRADE",
    "NEGATIVE_KEYWORDS",
    "CATEGORY_RAW",
    "CATEGORY_INTERMEDIATE",
    "CATEGORY_FINISHED",
    "CATEGORY_LABELS",
    "SOURCE_IMPORT",
    "SOURCE_MANUAL",
    "STANDARD_TABLE_SKIP_FIELDS",
    "RESULT_BATCH_COLUMN_HEADERS",
    "INTERVAL_PATTERN",
    "UPPER_PATTERN",
    "LOWER_PATTERN",
    "PLAIN_NUMBER_PATTERN",
    "GRADE_PATTERN",
    "QUAL_PATTERN",
    "CN_FRACTION_PATTERN",
    "CN_FRACTION_SCALE",
    "NO_STANDARD_TEXTS",
]
