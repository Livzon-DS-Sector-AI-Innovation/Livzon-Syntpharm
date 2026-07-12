"""Product output ORM models for daily production statistics by workshop."""

import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel

WORKSHOP_CHOICES = [
    "101车间",
    "102车间",
    "103车间",
    "106车间",
    "201车间",
    "202车间",
    "203车间",
    "301车间",
    "302车间",
    "303车间",
    "溶剂回收车间",
]


class ProductOutput(BaseModel):
    """每日产量统计表"""

    __tablename__ = "product_outputs"
    __table_args__ = {"schema": "production"}

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("production.products.id"),
        nullable=False,
        index=True,
        comment="关联产品ID",
    )
    workshop: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="车间名称")
    product_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="产品名称（冗余字段）")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="批号")
    production_date: Mapped[date] = mapped_column(Date, nullable=False, comment="生产日期")
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="结束日期")
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="重量(kg)")
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg", comment="单位")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
