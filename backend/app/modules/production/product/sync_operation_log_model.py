"""SyncOperationLog ORM 模型"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class SyncOperationLog(BaseModel):
    """同步操作日志表"""

    __tablename__ = "sync_operation_logs"
    __table_args__ = {"schema": "production"}

    id: Mapped[UUID] = mapped_column(primary_key=False, comment="日志 ID")
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, comment="产品 ID")
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="操作类型：push/pull")
    records: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, comment="操作记录")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="创建时间")

    @staticmethod
    async def log_operation(
        db: AsyncSession,
        product_id: str,
        operation_type: str,
        records: list[dict[str, Any]],
    ) -> str:
        """记录同步操作日志"""
        import uuid as uuid_module

        log_id = str(uuid_module.uuid4())
        log = SyncOperationLog(
            id=UUID(log_id),
            product_id=product_id,
            operation_type=operation_type,
            records=records,
            created_at=datetime.now(),
        )
        db.add(log)
        await db.commit()
        return log_id

    @staticmethod
    async def get_operation_log(db: AsyncSession, log_id: str) -> dict[str, Any] | None:
        """获取操作日志"""
        result = await db.execute(select(SyncOperationLog).where(SyncOperationLog.id == UUID(log_id)))
        log = result.scalar_one_or_none()
        if log:
            return {
                "id": str(log.id),
                "product_id": log.product_id,
                "operation_type": log.operation_type,
                "records": log.records,
                "created_at": log.created_at,
            }
        return None

    @staticmethod
    async def get_latest_operation(db: AsyncSession, product_id: str) -> dict[str, Any] | None:
        """获取最新操作日志"""
        result = await db.execute(
            select(SyncOperationLog)
            .where(SyncOperationLog.product_id == product_id)
            .order_by(SyncOperationLog.created_at.desc())
            .limit(1)
        )
        log = result.scalar_one_or_none()
        if log:
            return {
                "id": str(log.id),
                "product_id": log.product_id,
                "operation_type": log.operation_type,
                "records": log.records,
                "created_at": log.created_at,
            }
        return None
