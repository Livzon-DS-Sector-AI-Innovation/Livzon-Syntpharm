"""Registration module public API — cross-module access points.

Other modules should import from this file instead of directly accessing
internal service/repository/models.
"""

from app.modules.registration.repository import (
    authorization as authorization_repository,
)
from app.modules.registration.repository import drug as drug_repository
from app.modules.registration.repository import (
    validation_audit as validation_audit_repository,
)
from app.modules.registration.service import authorization as authorization_service
from app.modules.registration.service import drug as drug_service
from app.modules.registration.service import (
    validation_audit as validation_audit_service,
)

__all__ = [
    "drug_service",
    "authorization_service",
    "validation_audit_service",
    "drug_repository",
    "authorization_repository",
    "validation_audit_repository",
]
