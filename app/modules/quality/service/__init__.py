"""Quality module service exports."""

from app.modules.quality.service.cpv_batch import (
    get_batches,
    get_batches_wide,
)
from app.modules.quality.service.cpv_parameter import (
    create_parameter,
    delete_parameter,
    get_parameter_by_id,
    get_parameters,
    update_parameter,
)

# CPV Products
from app.modules.quality.service.cpv_product import (
    create_product,
    delete_product,
    get_product_by_id,
    get_products,
    update_product,
)
from app.modules.quality.service.cpv_statistics import (
    get_statistics,
    get_trend_data,
)
from app.modules.quality.service.quality_management import (
    add_execution_track,
    approve_capa,
    auto_fill_from_deviation,
    batch_update_status,
    complete_ai_analysis,
    complete_part,
    confirm_dept_head,
    confirm_execution,
    confirm_production_status,
    create_attachment_review,
    create_capa,
    create_deviation,
    delete_attachment_review,
    delete_capa,
    delete_department_contact,
    delete_deviation,
    delete_execution_track,
    # CAPA workflow - NEW
    get_capa_departments,
    get_capa_detail,
    # CAPAs - existing
    get_capa_list,
    get_capa_statistics,
    get_department_confirmations,
    # Department contacts - existing
    get_department_contact_list,
    get_deviation_detail,
    # Deviations - existing
    get_deviation_list,
    # Statistics - existing
    get_deviation_statistics,
    get_stopped_departments,
    link_deviation,
    # Attachment reviews - existing
    list_attachment_reviews,
    resubmit_capa,
    resubmit_deviation,
    submit_capa,
    submit_evaluation,
    submit_final_code,
    # Deviation workflow - NEW
    submit_for_review,
    submit_investigation,
    submit_review,
    update_capa,
    update_deviation,
    upsert_department_contact,
)

__all__ = [
    # Deviations
    "get_deviation_list",
    "get_deviation_detail",
    "create_deviation",
    "update_deviation",
    "delete_deviation",
    "submit_investigation",
    "submit_review",
    "submit_final_code",
    "resubmit_deviation",
    # CAPAs
    "get_capa_list",
    "get_capa_detail",
    "create_capa",
    "update_capa",
    "delete_capa",
    # Department contacts
    "get_department_contact_list",
    "upsert_department_contact",
    "delete_department_contact",
    # Statistics
    "get_deviation_statistics",
    "get_capa_statistics",
    # Attachment reviews
    "list_attachment_reviews",
    "create_attachment_review",
    "delete_attachment_review",
    # Deviation workflow - NEW
    "submit_for_review",
    "complete_ai_analysis",
    "batch_update_status",
    "get_department_confirmations",
    "confirm_production_status",
    "get_stopped_departments",
    # CAPA workflow - NEW
    "get_capa_departments",
    "auto_fill_from_deviation",
    "link_deviation",
    "complete_part",
    "submit_capa",
    "confirm_dept_head",
    "approve_capa",
    "resubmit_capa",
    "add_execution_track",
    "delete_execution_track",
    "confirm_execution",
    "submit_evaluation",
    # CPV Products
    "create_product",
    "get_product_by_id",
    "get_products",
    "update_product",
    "delete_product",
    # CPV Parameters
    "create_parameter",
    "get_parameter_by_id",
    "get_parameters",
    "update_parameter",
    "delete_parameter",
    # CPV Batches
    "get_batches",
    "get_batches_wide",
    # CPV Statistics
    "get_statistics",
    "get_trend_data",
]
