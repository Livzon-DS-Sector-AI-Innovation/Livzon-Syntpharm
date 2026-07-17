"""Registration ledger schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ── Domestic Approval ──────────────────────────────────────────────


class DomesticApprovalBase(BaseModel):
    product_name: str
    certificate_name: str | None = None
    batch_no: str | None = None
    issuing_authority: str | None = None
    issue_date: date | None = None
    valid_until: date | None = None
    product_scope: str | None = None
    quality_standard: str | None = None
    registration_no: str | None = None
    is_expired: str | None = None
    production_workshop: str | None = None
    product_validity: str | None = None
    storage_condition: str | None = None


class DomesticApprovalCreate(DomesticApprovalBase):
    pass


class DomesticApprovalUpdate(DomesticApprovalBase):
    product_name: str | None = None  # type: ignore[assignment]


class DomesticApprovalResponse(DomesticApprovalBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Overseas Approval ─────────────────────────────────────────────


class OverseasApprovalBase(BaseModel):
    product_name: str
    certificate_name: str | None = None
    batch_no: str | None = None
    issuing_authority: str | None = None
    issue_date: date | None = None
    valid_until: date | None = None
    product_scope: str | None = None
    quality_standard: str | None = None
    is_expired: str | None = None
    production_workshop: str | None = None
    product_validity: str | None = None
    storage_condition: str | None = None


class OverseasApprovalCreate(OverseasApprovalBase):
    pass


class OverseasApprovalUpdate(OverseasApprovalBase):
    product_name: str | None = None  # type: ignore[assignment]


class OverseasApprovalResponse(OverseasApprovalBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── International Review ───────────────────────────────────────────


class InternationalReviewBase(BaseModel):
    product_name: str
    approved_countries: str | None = None
    approved_country_count: int | None = None
    approved_clients: str | None = None
    approved_client_count: int | None = None
    reviewing_countries: str | None = None
    reviewing_country_count: int | None = None
    reviewing_clients: str | None = None
    reviewing_client_count: int | None = None


class InternationalReviewCreate(InternationalReviewBase):
    pass


class InternationalReviewUpdate(InternationalReviewBase):
    product_name: str | None = None  # type: ignore[assignment]


class InternationalReviewResponse(InternationalReviewBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── COPP Certificate ───────────────────────────────────────────────


class CoppCertificateBase(BaseModel):
    product_name: str
    certificate_name: str | None = None
    batch_no: str | None = None
    issuing_authority: str | None = None
    issue_date: date | None = None
    valid_until: date | None = None
    product_scope: str | None = None
    applicable_countries: str | None = None
    is_expired: str | None = None


class CoppCertificateCreate(CoppCertificateBase):
    pass


class CoppCertificateUpdate(CoppCertificateBase):
    product_name: str | None = None  # type: ignore[assignment]


class CoppCertificateResponse(CoppCertificateBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── WC Certificate ─────────────────────────────────────────────────


class WcCertificateBase(BaseModel):
    product_name: str
    certificate_name: str | None = None
    batch_no: str | None = None
    issuing_authority: str | None = None
    issue_date: date | None = None
    valid_until: date | None = None
    product_scope: str | None = None
    is_expired: str | None = None


class WcCertificateCreate(WcCertificateBase):
    pass


class WcCertificateUpdate(WcCertificateBase):
    product_name: str | None = None  # type: ignore[assignment]


class WcCertificateResponse(WcCertificateBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Ledger Summary (for Dashboard) ─────────────────────────────────


class LedgerSummary(BaseModel):
    domestic_count: int
    overseas_count: int
    overseas_countries: int
    international_review_count: int
    copp_count: int
    wc_count: int
    reviewing_count: int
    planned_count: int
