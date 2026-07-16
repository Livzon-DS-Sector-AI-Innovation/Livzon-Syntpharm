"""CPV service exports."""

from app.modules.quality.cpv.service.cpv_batch import (
    get_batches,
    get_batches_wide,
)
from app.modules.quality.cpv.service.cpv_parameter import (
    create_parameter,
    delete_parameter,
    get_parameter_by_id,
    get_parameters,
    update_parameter,
)
from app.modules.quality.cpv.service.cpv_product import (
    create_product,
    delete_product,
    get_product_by_id,
    get_products,
    update_product,
)
from app.modules.quality.cpv.service.cpv_statistics import (
    get_statistics,
    get_trend_data,
)

__all__ = [
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
