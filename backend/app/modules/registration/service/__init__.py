"""Registration service."""

from app.modules.registration.service.authorization import (
    AuthorizationLetterService,
    SupplementaryReplyService,
)
from app.modules.registration.service.certificate import (
    create_certificate,
    delete_certificate,
    get_certificate,
    get_certificates,
    update_certificate,
)
from app.modules.registration.service.dashboard import get_dashboard_summary
from app.modules.registration.service.drug import (
    create_drug,
    delete_drug,
    get_drug,
    get_drugs,
    update_drug,
)
from app.modules.registration.service.holiday import (
    create_holiday,
    delete_holiday,
    get_holidays,
    update_holiday,
)
from app.modules.registration.service.project import (
    create_project,
    delete_project,
    get_project,
    get_projects,
    update_project,
)
from app.modules.registration.service.reference_standard import (
    ReferenceStandardService,
)
from app.modules.registration.service.validation_audit import (
    ValidationAuditService,
)

__all__ = [
    "AuthorizationLetterService",
    "ReferenceStandardService",
    "SupplementaryReplyService",
    "ValidationAuditService",
    "create_certificate",
    "create_drug",
    "create_holiday",
    "create_project",
    "delete_certificate",
    "delete_drug",
    "delete_holiday",
    "delete_project",
    "get_certificate",
    "get_certificates",
    "get_dashboard_summary",
    "get_drug",
    "get_drugs",
    "get_holidays",
    "get_project",
    "get_projects",
    "update_certificate",
    "update_drug",
    "update_holiday",
    "update_project",
]
