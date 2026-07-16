"""CPV schemas."""

from app.modules.quality.cpv.schemas.cpv_batch import (
    CpvBatchResponse,
    CpvBatchWideResponse,
    DataType,
)
from app.modules.quality.cpv.schemas.cpv_import import (
    CpvImportConfirmRequest,
    CpvImportPreviewRequest,
    CpvImportPreviewResponse,
    CpvImportTaskResponse,
    ImportMode,
    ImportStatus,
)
from app.modules.quality.cpv.schemas.cpv_parameter import (
    CpvParameterCreate,
    CpvParameterResponse,
    CpvParameterUpdate,
    ParameterType,
)
from app.modules.quality.cpv.schemas.cpv_product import (
    CpvProductCreate,
    CpvProductListResponse,
    CpvProductResponse,
    CpvProductUpdate,
    ProductStatus,
)
from app.modules.quality.cpv.schemas.cpv_statistics import (
    CpvStatisticsRequest,
    CpvStatisticsResponse,
    CpvTrendItem,
    CpvTrendResponse,
)

__all__ = [
    # CPV Product
    "ProductStatus",
    "CpvProductCreate",
    "CpvProductUpdate",
    "CpvProductResponse",
    "CpvProductListResponse",
    # CPV Parameter
    "ParameterType",
    "CpvParameterCreate",
    "CpvParameterUpdate",
    "CpvParameterResponse",
    # CPV Batch
    "DataType",
    "CpvBatchResponse",
    "CpvBatchWideResponse",
    # CPV Import
    "ImportMode",
    "ImportStatus",
    "CpvImportPreviewRequest",
    "CpvImportPreviewResponse",
    "CpvImportConfirmRequest",
    "CpvImportTaskResponse",
    # CPV Statistics
    "CpvStatisticsRequest",
    "CpvStatisticsResponse",
    "CpvTrendItem",
    "CpvTrendResponse",
]
