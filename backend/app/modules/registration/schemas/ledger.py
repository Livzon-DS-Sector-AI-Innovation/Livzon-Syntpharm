"""Registration ledger schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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


# ── Excel 导入 / 审评中品种 ─────────────────────────────────────────


class LedgerImportResult(BaseModel):
    """台账 Excel 导入回执"""

    count: int = 0
    message: str = ""
    total_rows: int = 0
    success_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[str] = Field(default_factory=list)


class ReviewingDrugItem(BaseModel):
    """审评中品种

    `node_N`（各审评节点的实际完成日期）随品种节点数动态变化，无法在契约里穷举，
    因此允许额外字段——这样既能声明固定字段，也不会丢掉节点日期。
    """

    model_config = ConfigDict(extra="allow")

    id: str
    product_name: str
    drug_type: str | None = None
    acceptance_date: str | None = None
    current_node: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
