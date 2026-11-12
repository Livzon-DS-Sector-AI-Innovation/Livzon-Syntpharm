"""Service for the 2026 入职台账 (ticket #199).

The ledger is manual: every field is entered by hand, nothing is resolved
from Feishu, and deletes are soft so mistakes stay auditable. The shared
ledger shell supplies list/get/create/update/delete; this class only wires the
onboarding table and its display name.
"""

from __future__ import annotations

from app.modules.hr.ledger_service import LedgerRecordService
from app.modules.hr.models import OnboardingRecord
from app.modules.hr.onboarding_repository import OnboardingRecordRepository


class OnboardingRecordService(LedgerRecordService[OnboardingRecord]):
    repository = OnboardingRecordRepository
    not_found_label = "入职记录"
