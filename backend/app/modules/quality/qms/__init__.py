"""Quality Management System (QMS) module."""

from app.modules.quality.qms.api import router as quality_router
from app.modules.quality.qms.deviation_api import router as deviation_router
from app.modules.quality.qms.deviation_settings_api import router as deviation_settings_router
from app.modules.quality.qms.doc_check.api import router as doc_check_router
from app.modules.quality.qms.fqc_api import router as fqc_router
from app.modules.quality.qms.instrument_api import router as instrument_router
from app.modules.quality.qms.ipqc_api import router as ipqc_router
from app.modules.quality.qms.iqc_api import router as iqc_router
from app.modules.quality.qms.reagent_api import router as quality_reagent_router
from app.modules.quality.qms.reagent_reminder_api import (
    router as reagent_reminder_router,
)
from app.modules.quality.qms.sampling_api import router as sampling_router
from app.modules.quality.qms.stability_api import router as stability_router
from app.modules.quality.qms.static_data.api import router as static_data_router

__all__ = [
    "quality_router",
    "sampling_router",
    "iqc_router",
    "ipqc_router",
    "fqc_router",
    "stability_router",
    "deviation_router",
    "deviation_settings_router",
    "quality_reagent_router",
    "doc_check_router",
    "static_data_router",
    "reagent_reminder_router",
    "instrument_router",
]
