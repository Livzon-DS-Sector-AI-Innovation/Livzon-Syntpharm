"""SyncOperationLog ORM 模型"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class SyncOperationLog(BaseModel):
    """同步操作日志表"""

    __tablename__ = "sync_operation_logs"
    __table_args__ = {"schema": "production"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="日志ID")
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, comment="产品ID")
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="操作类型：push/pull")
    records: Mapped[list] = mapped_column(JSON, nullable=False, comment="操作记录")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="创建时间")
