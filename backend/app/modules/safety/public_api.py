"""
安全管理模块 — 公共 API。

供其他模块调用的稳定接口。不要直接 import safety 模块内部的
``service/``、``repository/``、``models.py`` 等实现细节。
"""

from app.modules.safety.service.hazard_workbench import (
    list_hazard_processes,
    list_hazard_review_todos,
)
from app.modules.safety.template_export import (
    # 配置
    HAZARD_COLUMN_MAPPING,
    HAZARD_TEMPLATE_CONFIG,
    NUMERIC_COLUMNS,
    RISK_LABEL_COLORS,
    # 引擎
    ExcelTemplateFiller,
    ExcelToPdfConverter,
    InspectionResult,
    PageSetup,
    TemplateConfig,
    TemplateInspector,
    # 便捷函数
    convert_xlsx_to_pdf,
    fill_and_export,
    fill_template,
    inspect_template,
    quick_export,
)

__all__ = [
    # 首页工作台（审核待办 / 我参与的流程）
    "list_hazard_review_todos",
    "list_hazard_processes",
    # 配置
    "TemplateConfig",
    "PageSetup",
    "HAZARD_TEMPLATE_CONFIG",
    "HAZARD_COLUMN_MAPPING",
    "NUMERIC_COLUMNS",
    "RISK_LABEL_COLORS",
    # 自动检测
    "TemplateInspector",
    "InspectionResult",
    # 引擎
    "ExcelTemplateFiller",
    "ExcelToPdfConverter",
    # 便捷函数
    "fill_and_export",
    "fill_template",
    "convert_xlsx_to_pdf",
    "quick_export",
    "inspect_template",
]
