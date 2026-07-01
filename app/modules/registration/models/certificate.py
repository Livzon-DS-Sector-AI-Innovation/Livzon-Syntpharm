"""Registration certificate ORM model."""

import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class RegistrationCertificate(BaseModel):
    """注册证书信息表"""

    __tablename__ = "registration_certificates"
    __table_args__ = (
        CheckConstraint(
            "certificate_type IN ('domestic_approval', 'overseas_registration', 'wc', 'copp', 'gmp', 'other')",
            name="ck_registration_certificates_type",
        ),
        CheckConstraint(
            "status IN ('valid', 'expiring', 'expired', 'pending')",
            name="ck_registration_certificates_status",
        ),
        {"schema": "registration"},
    )

    product_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="品种名称"
    )
    market: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="国家/市场"
    )
    certificate_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="证书类型：domestic_approval/overseas_registration/wc/copp/gmp/other",
    )
    certificate_no: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="证书编号"
    )
    approved_at: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="获批日期"
    )
    valid_until: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="有效期至"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="valid",
        comment="证书状态：valid/expiring/expired/pending",
    )
    file_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="证书文件路径"
    )
    related_project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, comment="关联注册项目ID"
    )
