"""Quality module - combines CPV and QMS."""

from app.modules.quality.cpv import router as cpv_router
from app.modules.quality.qms import (
    deviation_router,
    doc_check_router,
    fqc_router,
    instrument_router,
    ipqc_router,
    iqc_router,
    quality_reagent_router,
    quality_router,
    reagent_reminder_router,
    sampling_router,
    stability_router,
    static_data_router,
)

__all__ = [
    "cpv_router",
    "quality_router",
    "sampling_router",
    "iqc_router",
    "ipqc_router",
    "fqc_router",
    "stability_router",
    "deviation_router",
    "quality_reagent_router",
    "doc_check_router",
    "static_data_router",
    "reagent_reminder_router",
    "instrument_router",
]
