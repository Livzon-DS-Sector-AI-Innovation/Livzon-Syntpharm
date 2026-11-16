"""风险分级管控台账共享常量与 LEC 计算。

本模块只存放两张危险源台账（作业活动 / 设备设施）共用的选项与判定原语，
供 API、schema、service 复用；不包含任何数据库访问。

- 作业活动台账使用 LEC：D = L × E × C，D > 20，级别 1–4（4 最高）。
- 设备设施台账后续复用 管控层级 / 残余风险 / 执行层级 / 控制措施 常量。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

# ── 管控层级：需求文档给定的 28 个部门（与隐患/检查表单的 DEPARTMENT_OPTIONS 无关）──
RISK_GRADING_DEPARTMENTS: Final[tuple[str, ...]] = (
    "106车间",
    "AI创新部",
    "人事行政部",
    "动力部",
    "201车间",
    "202车间",
    "头孢合成制造部公共岗",
    "溶剂回收车间",
    "301车间",
    "302车间",
    "303车间",
    "头孢无菌制造部公共岗",
    "安全中心",
    "环保中心",
    "技术研发部",
    "注册部",
    "仓库",
    "生产部办公室",
    "设备工程部",
    "财务部",
    "质量保证部",
    "质量控制部",
    "采购部",
    "101车间",
    "102车间",
    "103车间",
    "105车间",
    "非头孢制造部公共岗",
)

# ── 控制措施：作业活动台账五项原文（含序号，逐字对齐需求文档）──
CONTROL_MEASURE_OPTIONS: Final[tuple[dict[str, str], ...]] = (
    {"key": "engineering", "label": "1、工程控制措施，实现本质安全"},
    {"key": "management", "label": "2、管理措施，规范安全管理"},
    {"key": "education", "label": "3、教育措施，提高从业人员的操作技能和安全意识"},
    {"key": "ppe", "label": "4、个体防护设施，减少职业伤害"},
    {"key": "emergency", "label": "5、应急处置措施，降低事故伤害"},
)

CONTROL_MEASURE_KEYS: Final[frozenset[str]] = frozenset(item["key"] for item in CONTROL_MEASURE_OPTIONS)

# ── 残余风险：仅三个选项（无 4 级）──
RESIDUAL_RISK_OPTIONS: Final[tuple[dict[str, str], ...]] = (
    {"key": "level_1", "label": "1级低风险"},
    {"key": "level_2", "label": "2级一般风险"},
    {"key": "level_3", "label": "3级较大风险"},
)

RESIDUAL_RISK_LABELS: Final[dict[str, str]] = {item["key"]: item["label"] for item in RESIDUAL_RISK_OPTIONS}
RESIDUAL_RISK_KEYS: Final[frozenset[str]] = frozenset(RESIDUAL_RISK_LABELS)

# ── 执行层级：仅 车间 / 班组长 ──
EXECUTION_LEVEL_OPTIONS: Final[tuple[dict[str, str], ...]] = (
    {"key": "workshop", "label": "车间"},
    {"key": "team_leader", "label": "班组长"},
)

EXECUTION_LEVEL_LABELS: Final[dict[str, str]] = {item["key"]: item["label"] for item in EXECUTION_LEVEL_OPTIONS}
EXECUTION_LEVEL_KEYS: Final[frozenset[str]] = frozenset(EXECUTION_LEVEL_LABELS)

# ── 设备设施台账措施：与作业活动台账共用稳定 key，仅展示短标签 ──
EQUIPMENT_MEASURE_OPTIONS: Final[tuple[dict[str, str], ...]] = (
    {"key": "engineering", "label": "工程技术"},
    {"key": "management", "label": "管理措施"},
    {"key": "education", "label": "培训教育"},
    {"key": "ppe", "label": "个体防护"},
    {"key": "emergency", "label": "应急处置"},
)

EQUIPMENT_MEASURE_LABELS: Final[dict[str, str]] = {item["key"]: item["label"] for item in EQUIPMENT_MEASURE_OPTIONS}

# ── 设备设施台账：可能性 L 1–5、严重性 S A–E ──
LIKELIHOOD_LEVELS: Final[tuple[int, ...]] = (1, 2, 3, 4, 5)
SEVERITY_LEVELS: Final[tuple[str, ...]] = ("A", "B", "C", "D", "E")

# ── 安全风险矩阵（S 纵轴 A–E，L 横轴 1–5）：R 取交叉格，不是 L×S ──
SAFETY_RISK_MATRIX: Final[dict[str, tuple[int, int, int, int, int]]] = {
    "A": (3, 5, 7, 10, 15),
    "B": (5, 7, 10, 15, 23),
    "C": (7, 11, 16, 23, 35),
    "D": (17, 25, 37, 55, 81),
    "E": (22, 32, 46, 68, 100),
}


def lookup_risk_evaluation(likelihood: int, severity: str) -> int:
    """按 L（1–5）与 S（A–E）查安全风险矩阵，返回十进制 R 值。"""
    if likelihood not in LIKELIHOOD_LEVELS:
        raise ValueError(f"可能性 L 必须是 1–5，收到: {likelihood}")
    row = SAFETY_RISK_MATRIX.get(severity)
    if row is None:
        raise ValueError(f"严重性 S 必须是 A–E，收到: {severity}")
    return row[likelihood - 1]


# ── 设备设施台账分级：按 R 分段，R < 10 → 1级，10 ≤ R < 20 → 2级，
#    20 ≤ R < 40 → 3级，R ≥ 40 → 4级；按 min_r 从高到低排列，取首个满足项。
EQUIPMENT_EVALUATION_GRADE_BANDS: Final[tuple[tuple[int, str, int], ...]] = (
    (4, "4级", 40),
    (3, "3级", 20),
    (2, "2级", 10),
    (1, "1级", 0),
)


def derive_equipment_evaluation_grade(risk_evaluation_r: int) -> tuple[int, str]:
    """按 R 分段返回设备设施评价级别与标签；矩阵 R 最小为 3，必然命中 1级。"""
    for grade, label, min_r in EQUIPMENT_EVALUATION_GRADE_BANDS:
        if risk_evaluation_r >= min_r:
            return grade, label
    raise ValueError(f"危险评价 R={risk_evaluation_r} 不满足分级下限")


# ── LEC 校验区间 ──
LIKELIHOOD_MIN: Final[Decimal] = Decimal("0.1")
LIKELIHOOD_MAX: Final[Decimal] = Decimal("10")
EXPOSURE_MIN: Final[Decimal] = Decimal("0.5")
EXPOSURE_MAX: Final[Decimal] = Decimal("10")
CONSEQUENCE_MIN: Final[Decimal] = Decimal("1")
CONSEQUENCE_MAX: Final[Decimal] = Decimal("100")

# L/E/C 在数据库中以 Numeric(18,6) 存储；输入超过 6 位小数会被拒绝，
# 保证存储值、返回值与 D 的乘积来自同一组量化后的数值。
DECIMAL_QUANTUM: Final[Decimal] = Decimal("0.000001")

# 分级下限：D 必须大于 20
MIN_RISK_VALUE: Final[Decimal] = Decimal("20")

# 分级阈值（按下限从高到低）：D > lower_bound_exclusive → grade。
# 边界值归低档；grade 越高风险越大（与旧 RiskLevel 方向相反）。
EVALUATION_GRADE_THRESHOLDS: Final[tuple[tuple[int, Decimal], ...]] = (
    (4, Decimal("320")),
    (3, Decimal("160")),
    (2, Decimal("70")),
    (1, MIN_RISK_VALUE),
)


def quantize_decimal(value: Decimal) -> Decimal:
    """把 L/E/C 量化到数据库的 6 位小数精度。"""
    return value.quantize(DECIMAL_QUANTUM)


def compute_risk_value(likelihood: Decimal, exposure: Decimal, consequence: Decimal) -> Decimal:
    """D = L × E × C，使用 Decimal 精确相乘，不做任何舍入。"""
    return likelihood * exposure * consequence


def derive_evaluation_grade(risk_value: Decimal) -> tuple[int, str]:
    """按需求文档分级：D > 320 → 4，160 < D ≤ 320 → 3，70 < D ≤ 160 → 2，20 < D ≤ 70 → 1。

    边界值归低档。调用方必须先通过 D > 20 的下限校验。
    """
    for grade, lower_bound_exclusive in EVALUATION_GRADE_THRESHOLDS:
        if risk_value > lower_bound_exclusive:
            return grade, f"{grade}级"
    raise ValueError(f"风险值 D={risk_value} 不满足 D > 20 的分级下限")
