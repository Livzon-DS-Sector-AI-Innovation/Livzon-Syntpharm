"""Registration module models."""
# ruff: noqa: F401

from app.modules.registration.models.authorization import (
    AuthorizationLetter,
    AuthorizationLetterTrail,
    SupplementaryReply,
)
from app.modules.registration.models.certificate import RegistrationCertificate
from app.modules.registration.models.copp_certificate import CoppCertificate
from app.modules.registration.models.domestic_approval import DomesticApproval
from app.modules.registration.models.drug import Drug, DrugNode, Holiday
from app.modules.registration.models.international_review import InternationalReview
from app.modules.registration.models.overseas_approval import OverseasApproval
from app.modules.registration.models.project import ProjectProgressLog, RegistrationProject
from app.modules.registration.models.reference_standard import ReferenceStandard
from app.modules.registration.models.reference_substance import ReferenceSubstance
from app.modules.registration.models.review import ReviewNode
from app.modules.registration.models.validation_audit import (
    ValidationAuditFile,
    ValidationAuditIssue,
    ValidationAuditKnowledgeBase,
    ValidationAuditReport,
    ValidationAuditTask,
)
from app.modules.registration.models.wc_certificate import WcCertificate

__all__ = [
    "AuthorizationLetter",
    "AuthorizationLetterTrail",
    "CoppCertificate",
    "DomesticApproval",
    "Drug",
    "DrugNode",
    "Holiday",
    "InternationalReview",
    "OverseasApproval",
    "ProjectProgressLog",
    "ReferenceStandard",
    "ReferenceSubstance",
    "RegistrationCertificate",
    "RegistrationProject",
    "ReviewNode",
    "SupplementaryReply",
    "ValidationAuditFile",
    "ValidationAuditIssue",
    "ValidationAuditKnowledgeBase",
    "ValidationAuditReport",
    "ValidationAuditTask",
    "WcCertificate",
]

# Regulatory tracker models
from app.modules.registration.regulatory_tracker.models import (
    DataChannel,
    DataSource,
    RegulatoryDocument,
    SyncJob,
    SyncJobPage,
)

__all__.extend(
    [
        "DataChannel",
        "DataSource",
        "RegulatoryDocument",
        "SyncJob",
        "SyncJobPage",
    ]
)
