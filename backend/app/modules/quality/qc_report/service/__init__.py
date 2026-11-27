"""质量检验台账 service 层。"""

from app.modules.quality.qc_report.service.bridge import bridge_items, normalize_name
from app.modules.quality.qc_report.service.docx_parser import parse_standard_docx
from app.modules.quality.qc_report.service.judge import (
    JudgeItem,
    aggregate_level,
    compile_item_limits,
    judge_value,
)
from app.modules.quality.qc_report.service.limits import infer_value_type, parse_limit, to_number
from app.modules.quality.qc_report.service.xlsx_parser import parse_result_xlsx

__all__ = [
    "bridge_items",
    "normalize_name",
    "parse_standard_docx",
    "parse_result_xlsx",
    "JudgeItem",
    "aggregate_level",
    "compile_item_limits",
    "judge_value",
    "infer_value_type",
    "parse_limit",
    "to_number",
]
