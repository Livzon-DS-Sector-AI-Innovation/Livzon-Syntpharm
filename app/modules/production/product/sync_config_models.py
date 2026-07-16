"""Product sync config ORM model for Feishu Bitable sync settings."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class ProductSyncConfig(BaseModel):
    """产品飞书多维表格同步配置表"""

    __tablename__ = "product_sync_configs"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_product_sync_config_product"),
        {"schema": "production"},
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("production.products.id"),
        nullable=False,
        index=True,
        comment="关联产品ID",
    )
    app_token: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书多维表格 app_token")
    table_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书表格 table_id")
    field_mapping: Mapped[str | None] = mapped_column(Text, nullable=True, comment="字段映射配置 JSON")
    auto_sync: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否自动同步")
    last_sync_at: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="最后同步时间")
    sync_direction: Mapped[str] = mapped_column(
        String(20), nullable=False, default="bidirectional", comment="同步方向: push/pull/bidirectional"
    )
