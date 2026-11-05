"""历史《危险源辨识管控清单》CSV 行映射。

纯函数，不依赖数据库与会话，供 scripts/import/import_hazard_identifications.py 调用，
也便于单元测试直接覆盖字段映射规则。
"""

import re
from typing import Any

from app.modules.safety.schemas.hazard_identifications import RISK_LEVELS

# CSV 表头（危险源辨识_去重_12683.csv，GB18030 编码，32 列），用于列序校验
CSV_COLUMNS: list[str] = [
    "表内序号",
    "检查表编号",
    "风险点编号",
    "风险点类型",
    "风险点名称",
    "作业活动名称",
    "岗位",
    "作业单元/区域",
    "设备设施名称",
    "位号/部位",
    "作业步骤/检查项目",
    "检查标准",
    "危险源/潜在事件",
    "可能事故后果",
    "风险评价方法",
    "可能性L",
    "频次E",
    "后果C",
    "严重性S",
    "风险值D",
    "风险等级_四级",
    "现有风险等级_四级",
    "管控层级",
    "管控单位",
    "工程技术措施",
    "管理措施",
    "培训教育措施",
    "个体防护措施",
    "应急处置措施",
    "责任部门",
    "责任人",
    "备注",
]

# 视为空的占位符
NULL_PLACEHOLDERS: frozenset[str] = frozenset({"/", "／", "-", "—", "--", "无"})

# 四级风险等级 → 系统 level key
RISK_LEVEL_TO_KEY: dict[str, str] = {
    "重大": "level_1",
    "较大": "level_2",
    "一般": "level_3",
    "低": "level_4",
}

RISK_KEY_TO_LABEL: dict[str, str] = {str(level["key"]): str(level["label"]) for level in RISK_LEVELS}

# 管控层级归一（系统内约定：公司级/部门级/班组级）
CONTROL_LEVEL_MAP: dict[str, str] = {
    "公司(厂)级": "公司级",
    "公司（厂）级": "公司级",
    "公司级": "公司级",
    "部门(车间)级": "部门级",
    "部门（车间）级": "部门级",
    "部门级": "部门级",
    "班组级": "班组级",
    "岗位级": "岗位级",
}

# 数据库 NOT NULL 但 CSV 可能为空的文本字段 → 兜底空串
REQUIRED_TEXT_FIELDS: tuple[str, ...] = ("department", "position", "production_step")

_WHITESPACE_RE = re.compile(r"[ \t\u3000]+")


def clean_text(value: str | None) -> str | None:
    """去首尾空白、归一单元格内换行与连续空白，占位符转 None。"""
    if value is None:
        return None
    text = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if not text or text in NULL_PLACEHOLDERS:
        return None
    return text


def clean_required(value: str | None) -> str:
    """NOT NULL 文本字段：空值写空串（用户确认不做向下填充）。"""
    return clean_text(value) or ""


def to_float(value: str | None) -> float | None:
    """数值字段：允许千分位，无法解析时返回 None。"""
    text = clean_text(value)
    if text is None:
        return None
    try:
        return float(text.replace(",", "").replace("，", ""))
    except ValueError:
        return None


def map_risk_level(value: str | None) -> tuple[str | None, str | None]:
    """四级中文风险等级 → (level key, 中文标签)。未知值返回 (None, None)。"""
    text = clean_text(value)
    if text is None:
        return None, None
    key = RISK_LEVEL_TO_KEY.get(text)
    if key is None:
        return None, None
    return key, RISK_KEY_TO_LABEL.get(key)


def map_control_level(value: str | None) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    return CONTROL_LEVEL_MAP.get(text, text)


def resolve_risk_method(row: dict[str, str]) -> str | None:
    """风险评价方法：CSV 缺失时按有 C（LEC）或有 S（LS）推断。"""
    text = clean_text(row.get("风险评价方法"))
    if text is not None:
        return text.upper()
    if to_float(row.get("后果C")) is not None:
        return "LEC"
    if to_float(row.get("严重性S")) is not None:
        return "LS"
    return None


def build_hazard_id_no(seq: int) -> str:
    """生成未删除范围内唯一的危险源编号；重复导入时保持幂等。"""
    return f"HZ-{seq:05d}"


def map_row(row: dict[str, str], seq: int) -> dict[str, Any]:
    """CSV 一行 → hazard_identifications 插入字典（列名均为真实模型字段）。"""
    inherent_level, inherent_label = map_risk_level(row.get("风险等级_四级"))
    residual_level, residual_label = map_risk_level(row.get("现有风险等级_四级"))

    mapped: dict[str, Any] = {
        "hazard_id_no": build_hazard_id_no(seq),
        "checklist_no": clean_text(row.get("检查表编号")),
        "risk_point_no": clean_text(row.get("风险点编号")),
        "risk_point_type": clean_text(row.get("风险点类型")),
        "risk_point_name": clean_text(row.get("风险点名称")),
        "work_unit": clean_text(row.get("作业单元/区域")),
        "location_tag": clean_text(row.get("位号/部位")),
        "work_step": clean_text(row.get("作业步骤/检查项目")),
        "check_standard": clean_text(row.get("检查标准")),
        "risk_method": resolve_risk_method(row),
        "severity_s": to_float(row.get("严重性S")),
        "control_unit": clean_text(row.get("管控单位")),
        "training_measures": clean_text(row.get("培训教育措施")),
        # ── 复用现有字段 ──
        "department": clean_required(row.get("责任部门")),
        "position": clean_required(row.get("岗位")),
        "production_step": "",
        "specific_activity": clean_text(row.get("作业活动名称")),
        "equipment_facilities": clean_text(row.get("设备设施名称")),
        "unsafe_behavior": clean_text(row.get("危险源/潜在事件")),
        "possible_accident": clean_text(row.get("可能事故后果")),
        "l_inherent": to_float(row.get("可能性L")),
        "e_inherent": to_float(row.get("频次E")),
        "c_inherent": to_float(row.get("后果C")),
        "d_inherent": to_float(row.get("风险值D")),
        "inherent_risk_level": inherent_level,
        "inherent_risk_label": inherent_label,
        "residual_risk_level": residual_level,
        "residual_risk_label": residual_label,
        "control_level": map_control_level(row.get("管控层级")),
        "responsible_person": clean_text(row.get("责任人")),
        "notes": clean_text(row.get("备注")),
        # ── 现有控制措施 ──
        "existing_engineering_controls": clean_text(row.get("工程技术措施")),
        "existing_management_controls": clean_text(row.get("管理措施")),
        "existing_ppe": clean_text(row.get("个体防护措施")),
        "existing_emergency_measures": clean_text(row.get("应急处置措施")),
        # ── CSV 未提供的区段保持为空 ──
        "l_residual": None,
        "e_residual": None,
        "c_residual": None,
        "d_residual": None,
        "needs_recommendation": None,
        "recommendation_type": None,
        "recommendation_content": None,
        "recommendation_priority": None,
        "l_post": None,
        "e_post": None,
        "c_post": None,
        "d_post": None,
        "post_risk_level": None,
        "post_risk_label": None,
        # ── 状态：台账页与 PDF 导出只查 completed ──
        "overall_status": "completed",
        "ai_node_progress": "completed",
        "ai_error_message": None,
        **{f"script{index}_review_status": "approved" for index in range(1, 8)},
    }
    return mapped
