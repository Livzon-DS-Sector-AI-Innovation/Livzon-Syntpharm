"""质量检验台账（检验管理 > 质量检验）。

本期范围：需求文档 F1（数据字段与标准）、F2（录入与校验）、F3（三层判定与变色）。
"""

from app.modules.quality.qc_report.api import router
from app.modules.quality.qc_report.models import QcBatch, QcItem, QcProduct, QcValue

__all__ = ["QcProduct", "QcItem", "QcBatch", "QcValue", "router"]
