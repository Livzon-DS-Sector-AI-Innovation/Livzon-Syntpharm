"""原料检验数据表模型"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class InspectionTable(BaseModel):
    """检验数据表定义"""
    __tablename__ = 'inspection_tables'
    __table_args__ = (
        Index('idx_inspection_table_name', 'table_name'),
        Index('idx_inspection_table_active', 'is_active'),
        {"schema": "quality"},
    )

    # 表基本信息
    table_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment='数据表名称'
    )
    table_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='数据表描述'
    )

    # 列配置（JSONB）- 定义表头
    # 格式: [{"key": "col1", "label": "列1", "type": "text", "width": 120, "required": false}]
    columns_config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default='[]', comment='列配置'
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment='是否启用'
    )

    # Word 模板
    template_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment='Word模板路径'
    )
    template_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment='Word模板名称'
    )

    # 关联数据行
    rows: Mapped[list["InspectionTableRow"]] = relationship(
        "InspectionTableRow", back_populates="table", cascade="all, delete-orphan"
    )


class InspectionTableRow(BaseModel):
    """检验数据表数据行"""
    __tablename__ = 'inspection_table_rows'
    __table_args__ = (
        Index('idx_table_row_table', 'table_id'),
        {"schema": "quality"},
    )

    # 覆盖基类的 id 为整数类型（数据库中是自增整数）
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # 关联数据表
    table_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('quality.inspection_tables.id', ondelete='CASCADE'),
        nullable=False, comment='关联数据表ID'
    )

    # 行数据（JSONB）- 存储每个单元格的值
    # 格式: {"col1": "value1", "col2": "value2"}
    row_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default='{}', comment='行数据'
    )

    # 排序
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, comment='排序序号'
    )

    # 关联
    table: Mapped["InspectionTable"] = relationship(
        "InspectionTable", back_populates="rows"
    )
