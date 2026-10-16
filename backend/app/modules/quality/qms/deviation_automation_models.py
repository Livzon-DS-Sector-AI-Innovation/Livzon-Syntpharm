"""Deviation Automation ORM models.

Extracted from deviation_automation_api.py.

All tables inherit the shared `app.shared.base_model.BaseModel`, which supplies
the standard contract: UUID `id`, `created_at`, `updated_at`, `created_by`,
`updated_by` and `is_deleted`. `dev_task`'s primary key is therefore `id`
(renamed from the legacy `task_id`).
"""

from datetime import date

from sqlalchemy import Date, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class SOPRule(BaseModel):
    __tablename__ = "sop_rule"
    __table_args__ = {"schema": "quality"}

    sop_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    sop_full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    sop_version: Mapped[str] = mapped_column(String(32), nullable=False)
    business_tag: Mapped[str | None] = mapped_column(String(256))
    standard_limit: Mapped[str | None] = mapped_column(Text)
    standard_sentence: Mapped[str | None] = mapped_column(Text)
    sop_file_path: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)


class DevTask(BaseModel):
    __tablename__ = "dev_task"
    __table_args__ = {"schema": "quality"}

    deviation_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    creator: Mapped[str] = mapped_column(String(64), nullable=False)
    auditor: Mapped[str | None] = mapped_column(String(64))
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_file_path: Mapped[str | None] = mapped_column(String(512))
    standard_file_path: Mapped[str | None] = mapped_column(String(512))
    task_status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    ai_result: Mapped[str | None] = mapped_column(Text)


class ReportTemplate(BaseModel):
    __tablename__ = "report_template"
    __table_args__ = {"schema": "quality"}

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
