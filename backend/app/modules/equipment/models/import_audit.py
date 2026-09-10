"""Import audit log model."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class ImportAuditLog(BaseModel):
    """导入审计日志表"""

    __tablename__ = "import_audit_logs"
    __table_args__ = {"schema": "equipment"}

    batch_id: Mapped[str] = mapped_column(String(50), comment="导入批次ID")
    operation_type: Mapped[str] = mapped_column(String(20), comment="操作类型: create/update/skip/error")
    match_strategy: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="匹配策略")
    asset_no: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="资产编号")
    equipment_tag: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="设备位号")
    department_id: Mapped[uuid.UUID | None] = mapped_column(postgresql.UUID(as_uuid=True), nullable=True, comment="部门ID")
    location_text: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="位置文本")
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更详情")
    warnings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="警告信息")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Excel行号")
    override_type: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="覆盖类型: normal/force")
    created_by: Mapped[uuid.UUID | None] = mapped_column(postgresql.UUID(as_uuid=True), nullable=True, comment="操作用户ID")
