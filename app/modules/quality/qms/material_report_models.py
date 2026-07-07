"""原料报告单数据模型"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class ReportStatus(str, Enum):
    """报告单状态"""
    DRAFT = "draft"           # 草稿
    COMPLETED = "completed"    # 已完成
    APPROVED = "approved"     # 已审批
    ARCHIVED = "archived"     # 已归档


class ReportTemplate(BaseModel):
    """报告单模板表"""
    __tablename__ = 'report_templates'
    __table_args__ = (
        Index('idx_template_name', 'template_name', unique=True),
        Index('idx_template_active', 'is_active'),
        {"schema": "quality"},
    )

    # 模板基本信息
    template_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment='模板名称'
    )
    template_file_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment='模板文件存储路径'
    )
    template_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='模板描述说明'
    )

    # 字段配置（JSONB）
    field_mapping: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default='{}', comment='静态字段映射配置'
    )
    table_fields: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default='{}', comment='动态表格字段定义'
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment='是否启用'
    )

    # 关联报告单
    reports: Mapped[list["MaterialReport"]] = relationship(
        "MaterialReport", back_populates="template"
    )


class MaterialReport(BaseModel):
    """报告单主表"""
    __tablename__ = 'material_reports'
    __table_args__ = (
        Index('idx_report_template', 'template_id'),
        Index('idx_report_status', 'status'),
        Index('idx_report_date', 'report_date'),
        UniqueConstraint('report_no', name='uq_report_no'),
        {"schema": "quality"},
    )

    # 报告单基本信息
    report_no: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment='报告单编号'
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('quality.report_templates.id'),
        nullable=True, comment='关联模板ID'
    )
    report_title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment='报告单标题'
    )
    report_date: Mapped[datetime] = mapped_column(
        Date, nullable=False, comment='报告日期'
    )

    # 静态字段数据（JSONB）
    static_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment='静态字段数据'
    )

    # 状态
    status: Mapped[str] = mapped_column(
        SQLEnum(ReportStatus, name='report_status_enum', create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ReportStatus.DRAFT, comment='状态'
    )

    # 生成文件
    generated_file_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment='生成文件路径'
    )

    # 关联
    template: Mapped[Optional["ReportTemplate"]] = relationship(
        "ReportTemplate", back_populates="reports"
    )
    items: Mapped[list["MaterialReportItem"]] = relationship(
        "MaterialReportItem", back_populates="report", cascade="all, delete-orphan"
    )
    images: Mapped[list["ReportImage"]] = relationship(
        "ReportImage", back_populates="report", cascade="all, delete-orphan"
    )


class MaterialReportItem(BaseModel):
    """报告单明细表"""
    __tablename__ = 'material_report_items'
    __table_args__ = (
        Index('idx_item_report', 'report_id'),
        Index('idx_item_row', 'row_index'),
        UniqueConstraint('report_id', 'row_index', 'field_key', name='uq_item_composite'),
        {"schema": "quality"},
    )

    # 关联报告单
    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('quality.material_reports.id', ondelete='CASCADE'),
        nullable=False, comment='关联报告单ID'
    )

    # 行信息
    row_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment='行序号'
    )
    field_key: Mapped[str] = mapped_column(
        String(100), nullable=False, comment='字段标识'
    )
    field_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='字段值'
    )

    # 关联
    report: Mapped["MaterialReport"] = relationship(
        "MaterialReport", back_populates="items"
    )


class ReportImage(BaseModel):
    """报告单图片记录表"""
    __tablename__ = 'report_images'
    __table_args__ = (
        Index('idx_image_report', 'report_id'),
        Index('idx_image_field', 'field_key'),
        {"schema": "quality"},
    )

    # 关联报告单
    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('quality.material_reports.id', ondelete='CASCADE'),
        nullable=False, comment='关联报告单ID'
    )

    # 图片信息
    row_index: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment='关联行序号'
    )
    field_key: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment='对应字段'
    )
    image_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment='图片路径'
    )

    # AI识别结果
    ai_result: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment='AI识别结果'
    )

    # 关联
    report: Mapped[Optional["MaterialReport"]] = relationship(
        "MaterialReport", back_populates="images"
    )