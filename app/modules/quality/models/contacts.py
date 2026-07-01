"""Department contacts ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class DepartmentContact(BaseModel):
    __tablename__ = "department_contacts"
    __table_args__ = {"schema": "quality"}

    department: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    dept_head_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    qa_staff_ids: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    gmp_staff_ids: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    production_head_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    quality_head_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    additional_contacts: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    is_production_workshop: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=False, server_default="false"
    )


class DepartmentWeeklyConfirmation(BaseModel):
    __tablename__ = "department_weekly_confirmations"
    __table_args__ = (
        UniqueConstraint("department", "week_key", name="uq_dept_weekly_confirmation"),
        {"schema": "quality"},
    )

    department: Mapped[str] = mapped_column(String(255), nullable=False)
    week_key: Mapped[str] = mapped_column(String(20), nullable=False)
    production_status: Mapped[str] = mapped_column(String(20), nullable=False)
    deviation_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unsubmitted", server_default="unsubmitted"
    )
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
