"""Quality ORM models - imports all model files for Alembic detection."""

# Import all models so they register with SQLAlchemy metadata
from app.modules.quality.ai.config_model import (
    QmsAiConfig,
)

# Import platform AI models
from app.modules.quality.ai.models import (
    QmsAiLog,
)

# 第 0 代偏差表的模型只为 capas.deviation_id 的外键目标而保留（业务代码不用），
# 表本身已列入 alembic/env.py 的 RETIRED_TABLES，autogenerate 不会碰它们。
from app.modules.quality.qms import deviation_models as _legacy_deviation_models  # noqa: F401
from app.modules.quality.qms.deviation_department_models import (
    DepartmentContact,
    DepartmentWeeklyConfirmation,
)
from app.modules.quality.qms.deviation_ledger_models import (
    DeviationLedger,
)
from app.modules.quality.qms.inspection_table_models import (
    InspectionTable,
    InspectionTableRow,
)
from app.modules.quality.qms.material_report_models import (
    MaterialReport,
    MaterialReportItem,
    ReportImage,
    ReportTemplate,
)
from app.modules.quality.qms.reagent_models import (
    ReagentQuality,
)
from app.modules.quality.qms.reagent_reminder_config import (
    ReagentReminderConfig,
)
from app.modules.quality.qms.reminder_models import (
    QmsDeviationReminderRule,
    QmsReagentItemReminderConfig,
)
from app.modules.quality.qms.static_data.models import (
    ChromColumn,
    HplcReference,
    HplcReferenceUsage,
    Medium,
    Standard,
    StorageCondition,
    Unit,
)
from app.modules.quality.sop_ai.models import (
    SopAiCheckMain,
    SopAiCheckProblem,
    SopAiConfig,
)

__all__ = [
    "DepartmentContact",
    "DepartmentWeeklyConfirmation",
    "DeviationLedger",
    "InspectionTable",
    "InspectionTableRow",
    "MaterialReport",
    "MaterialReportItem",
    "ReportTemplate",
    "ReportImage",
    "SopAiConfig",
    "SopAiCheckMain",
    "SopAiCheckProblem",
    "ReagentReminderConfig",
    "ReagentQuality",
    "QmsDeviationReminderRule",
    "QmsReagentItemReminderConfig",
    "StorageCondition",
    "Unit",
    "HplcReference",
    "HplcReferenceUsage",
    "ChromColumn",
    "Standard",
    "Medium",
    "QmsAiLog",
    "QmsAiConfig",
]
