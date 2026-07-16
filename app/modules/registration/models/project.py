"""Registration project ORM model."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class RegistrationProject(BaseModel):
    """注册项目表"""

    __tablename__ = "registration_projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'preparing', 'submitted', 'accepted', "
            "'under_review', 'supplementary', 'approved', 'withdrawn', 'terminated')",
            name="ck_registration_projects_status",
        ),
        {"schema": "registration"},
    )

    product_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="品种名称")
    market: Mapped[str] = mapped_column(String(128), nullable=False, comment="注册市场/国家")
    registration_type: Mapped[str] = mapped_column(
        String(64), nullable=True, comment="注册类型（新注册/再注册/变更等）"
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="draft",
        comment="状态：draft/preparing/submitted/accepted/under_review/supplementary/approved/withdrawn/terminated",
    )
    submitted_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="申报日期")
    accepted_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="受理日期")
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="获批日期")
    expected_completion_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="预计完成时间")
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="负责人")
    latest_progress: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最新进展")
