"""Procurement module public API — cross-module access points.

Other modules should import from this file instead of directly accessing
internal service/repository/models.
"""

from app.modules.procurement.contract_generator import (
    TEMPLATE_DIR,
    TEMPLATE_FILES,
    get_contract_template_metadata,
)
from app.modules.procurement.models import Supplier
from app.modules.procurement.repository import SupplierRepository
from app.modules.procurement.schemas import (
    ContractCategory,
    PurchaseRequestCreate,
    PurchaseRequestResponse,
)

__all__ = [
    "SupplierRepository",
    "Supplier",
    "PurchaseRequestCreate",
    "PurchaseRequestResponse",
    "ContractCategory",
    "TEMPLATE_DIR",
    "TEMPLATE_FILES",
    "get_contract_template_metadata",
]