"""国际关联审评表"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class InternationalReview(BaseModel):
    """国际关联审评"""

    __tablename__ = "registration_international_reviews"
    __table_args__ = ({"schema": "registration"},)

    product_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="品名")
    approved_countries: Mapped[str | None] = mapped_column(Text, nullable=True, comment="获批国家")
    approved_country_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="获批国家数量")
    approved_clients: Mapped[str | None] = mapped_column(Text, nullable=True, comment="获批客户")
    approved_client_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="获批客户数量")
    reviewing_countries: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审评中-国家")
    reviewing_country_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="审评中-国家数量")
    reviewing_clients: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审评中-客户")
    reviewing_client_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="审评中-客户数量")
