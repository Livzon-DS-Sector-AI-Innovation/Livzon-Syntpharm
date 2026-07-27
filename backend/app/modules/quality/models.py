"""Quality ORM models - imports all model files for Alembic detection."""

# Import all models so they register with SQLAlchemy metadata
from app.modules.quality.ai.config_model import (
    QmsAiConfig,
)

# Import platform AI models
from app.modules.quality.ai.models import (
    QmsAiLog,
)
from app.modules.quality.qms.deviation_automation_models import (
    DevTask,
    SOPRule,
)
from app.modules.quality.qms.deviation_settings_models import (
    DeviationLeaderConfig,
    DeviationQAConfig,
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
    "InspectionTable",
    "InspectionTableRow",
    "MaterialReport",
    "MaterialReportItem",
    "ReportTemplate",
    "ReportImage",
    "DevTask",
    "SOPRule",
    "SopAiConfig",
    "SopAiCheckMain",
    "SopAiCheckProblem",
    "ReagentReminderConfig",
    "ReagentQuality",
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
