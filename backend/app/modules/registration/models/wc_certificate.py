"""WC证书表"""

from datetime import date

from sqlalchemy import CheckConstraint, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class WcCertificate(BaseModel):
    """WC证书"""

    __tablename__ = "registration_wc_certificates"
    __table_args__ = (
        CheckConstraint(
            "is_expired IN ('是', '否')",
            name="ck_wc_certificates_is_expired",
        ),
        {"schema": "registration"},
    )

    product_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="品名")
    certificate_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="证书名称")
    batch_no: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="批件号（通知书编号）")
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="国家/发证机关")
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="发证日期")
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True, comment="证书有效期至")
    product_scope: Mapped[str | None] = mapped_column(Text, nullable=True, comment="产品范围")
    is_expired: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="证书是否过期")
