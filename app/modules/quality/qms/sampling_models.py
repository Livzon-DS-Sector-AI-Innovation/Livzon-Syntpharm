"""Sampling management models"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class SamplingOrder(BaseModel):
    """取样单主表"""
    __tablename__ = "sampling_orders"
    __table_args__ = (
        Index("idx_sampling_order_no", "order_no", unique=True),
        Index("idx_sampling_source_no", "source_no"),
        Index("idx_sampling_material_code", "material_code"),
        Index("idx_sampling_status", "status"),
        Index("idx_sampling_source", "sampling_source"),
        Index("idx_sampling_date", "sampling_date"),
        {"schema": "quality"},
    )

    order_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="取样单号")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="来源类型：purchase_inbound/batch_no")
    source_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联单号")
    material_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="物料编码")
    material_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="物料名称")
    material_category: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="物料类别")
    batch_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="批次号")
    specification: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="规格")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True, comment="批量/数量")
    sampling_source: Mapped[str] = mapped_column(String(32), nullable=False, comment="取样来源")
    sampling_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True, comment="取样量")
    sampling_location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="取样地点")
    sampling_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="取样日期")
    sampler_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True, comment="取样人ID")
    sampler_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="取样人姓名")
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False, comment="状态")
    sampling_result: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="取样判定")
    exception_reasons: Mapped[str | None] = mapped_column(Text, nullable=True, comment="异常原因")
    deviation_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="关联偏差ID")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    items: Mapped[list["SamplingOrderItem"]] = relationship(back_populates="sampling_order", lazy="selectin")
    approval_records: Mapped[list["SamplingApprovalRecord"]] = relationship(back_populates="sampling_order", lazy="selectin")


class SamplingOrderItem(BaseModel):
    """取样明细表"""
    __tablename__ = "sampling_order_items"
    __table_args__ = (
        Index("idx_sampling_items_order_id", "sampling_order_id"),
        Index("idx_sampling_items_sample_no", "sample_no", unique=True),
        {"schema": "quality"},
    )

    sampling_order_id: Mapped[UUID] = mapped_column(ForeignKey("quality.sampling_orders.id"), nullable=False)
    item_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="项次")
    sample_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="样品编号")
    sampling_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="取样份数")
    retention_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="留样份数")
    retention_location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="留样存放位置")
    sample_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="样品状态")
    retention_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="留样日期")
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="留样有效期")
    is_expired: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否到期")
    disposal_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="处置日期")
    disposal_method: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="处置方式")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    sampling_order: Mapped["SamplingOrder"] = relationship(back_populates="items")


class SampleRetentionLedger(BaseModel):
    """留样台账表"""
    __tablename__ = "sample_retention_ledger"
    __table_args__ = (
        Index("idx_retention_sampling_order_id", "sampling_order_id"),
        Index("idx_retention_sample_no", "sample_no", unique=True),
        Index("idx_retention_material_code", "material_code"),
        Index("idx_retention_expiry_date", "expiry_date"),
        Index("idx_retention_status", "retention_status"),
        {"schema": "quality"},
    )

    sampling_item_id: Mapped[UUID] = mapped_column(ForeignKey("quality.sampling_order_items.id"), nullable=False)
    sampling_order_id: Mapped[UUID] = mapped_column(ForeignKey("quality.sampling_orders.id"), nullable=False)
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="取样单号")
    sample_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="样品编号")
    material_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="物料编码")
    material_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="物料名称")
    batch_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="批次号")
    retention_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="留样份数")
    retention_location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="存放位置")
    retention_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="留样日期")
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="有效期")
    retention_status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    disposal_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="处置日期")
    disposal_method: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="处置方式")
    disposal_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处置备注")
    reminder_sent: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否已发送提醒")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)


class SamplingApprovalRecord(BaseModel):
    """取样审批记录表"""
    __tablename__ = "sampling_approval_records"
    __table_args__ = (
        Index("idx_sampling_approval_order_id", "sampling_order_id"),
        {"schema": "quality"},
    )

    sampling_order_id: Mapped[UUID] = mapped_column(ForeignKey("quality.sampling_orders.id"), nullable=False)
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False, comment="审批级别")
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, comment="审批状态")
    approver_role: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="审批角色")
    approver_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    approver_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="审批人姓名")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    sampling_order: Mapped["SamplingOrder"] = relationship(back_populates="approval_records")
