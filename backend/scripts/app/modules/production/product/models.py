"""Product ORM models - defines products for each workshop."""

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class Product(BaseModel):
    """产品定义表 - 每个车间下的产品"""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("workshop", "name", name="uq_product_workshop_name"),
        {"schema": "production"},
    )

    workshop: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="车间名称")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="产品名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="产品描述")
