"""Registration repository."""

from app.modules.registration.repository.authorization import (
    AuthorizationLetterRepository,
    ReferenceStandardRepository,
)
from app.modules.registration.repository.drug import (
    create_drug,
    create_drug_node,
    delete_drug,
    get_drug_by_id,
    get_drug_nodes,
    get_drugs,
    update_drug,
    update_drug_node,
)
from app.modules.registration.repository.holiday import (
    create_holiday,
    delete_holiday,
    get_holiday_by_id,
    get_holidays,
    update_holiday,
)
from app.modules.registration.repository.reference_substance import (
    create_reference_substance,
    delete_reference_substance,
    get_reference_substance_by_id,
    get_reference_substances,
    update_reference_substance,
)

__all__ = [
    "AuthorizationLetterRepository",
    "ReferenceStandardRepository",
    "create_drug",
    "create_drug_node",
    "create_holiday",
    "create_reference_substance",
    "delete_drug",
    "delete_holiday",
    "delete_reference_substance",
    "get_drug_by_id",
    "get_drug_nodes",
    "get_drugs",
    "get_holiday_by_id",
    "get_holidays",
    "get_reference_substance_by_id",
    "get_reference_substances",
    "update_drug",
    "update_drug_node",
    "update_holiday",
    "update_reference_substance",
]
