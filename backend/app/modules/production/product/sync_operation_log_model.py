"""SyncOperationLog ORM 模型"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class SyncOperationLog(BaseModel):
    """同步操作日志表"""

    __tablename__ = "sync_operation_logs"
    __table_args__ = {"schema": "production"}

    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, comment="产品 ID")
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="操作类型：push/pull")
    records: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, comment="操作记录")

    @staticmethod
    async def log_operation(
        db: AsyncSession,
        product_id: str,
        operation_type: str,
        records: list[dict[str, Any]],
    ) -> str:
        """记录同步操作日志"""
        log = SyncOperationLog(
            product_id=product_id,
            operation_type=operation_type,
            records=records,
        )
        db.add(log)
        await db.flush()
        await db.commit()
        return str(log.id)

    @staticmethod
    async def get_operation_log(db: AsyncSession, log_id: str) -> dict[str, Any] | None:
        """获取操作日志"""
        from uuid import UUID

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
