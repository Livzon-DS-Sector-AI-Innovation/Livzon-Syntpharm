"""Reagent Quality Models (试剂质量标准管理数据模型)"""

from datetime import datetime

from sqlalchemy import Date, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class ReagentQuality(BaseModel):
    __tablename__ = "qms_reagent_quality"
    __table_args__ = (
        Index("idx_reagent_quality_lot_no", "lot_no"),
        Index("idx_reagent_quality_status", "status"),
        {"schema": "qms"},
    )

    reagent_label_urls: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    reagent_name: Mapped[str] = mapped_column(String(200))
    arrival_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    production_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    lot_no: Mapped[str] = mapped_column(String(100))
    incoming_lot_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expiration_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    specification: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reagent_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="available", server_default="available")