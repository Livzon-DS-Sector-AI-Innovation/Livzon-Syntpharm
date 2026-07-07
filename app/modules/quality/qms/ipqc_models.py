"""IPQC (In-Process Quality Control) inspection models"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class IPQCInspection(BaseModel):
    """IPQC检验主表 - 过程检验/中间体检验"""
    __tablename__ = "ipqc_inspections"
    __table_args__ = (
        Index("idx_ipqc_inspection_no", "inspection_no", unique=True),
        Index("idx_ipqc_batch_record_id", "batch_record_id"),
        Index("idx_ipqc_batch_no", "batch_no"),
        Index("idx_ipqc_product_code", "product_code"),
        Index("idx_ipqc_status", "status"),
        Index("idx_ipqc_inspection_date", "inspection_date"),
        Index("idx_ipqc_sampling_time", "sampling_time"),
        {"schema": "quality"},
    )

    # 批次关联信息
    batch_record_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="关联批次生产记录ID")
    batch_record_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="批次生产记录单号")
    batch_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="批次号")
    product_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="产品编码")
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="产品名称")
    product_specification: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="产品规格")

    # 工序信息
    process_stage: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="工序/工段")
    sampling_point: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="取样点")
    sampling_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="取样单号")
    sampling_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="取样时间")
    sampling_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True, comment="取样数量")
    sampling_unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="取样单位")
    sampling_location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="取样位置")
    production_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="生产日期")

    # 检验信息
    inspection_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="检验单号")
    inspection_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="检验日期")
    inspector_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True, comment="检验员ID")
    inspector_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="检验员姓名")

    # 质量标准
    standard_id: Mapped[UUID | None] = mapped_column(ForeignKey("quality.inspection_standards.id"), nullable=True, comment="检验标准ID")
    standard_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="检验标准名称")
    standard_version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="标准版本")

    # 检验结论
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False, comment="状态：draft/submitted/workshop_approved/qc_supervisor_approved/qa_final_approved/rejected")
    inspection_conclusion: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="检验结论：qualified/unqualified/conditional")
    conclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结论说明")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    deviation_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="关联偏差ID")
    oos_report_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="OOS报告编号")

    # 批次状态
    batch_locked: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="批次是否锁定")
    batch_lock_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="批次锁定原因")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    items: Mapped[list["IPQCInspectionItem"]] = relationship(back_populates="ipqc_inspection", lazy="selectin")
    approval_records: Mapped[list["IPQCApprovalRecord"]] = relationship(back_populates="ipqc_inspection", lazy="selectin")


class IPQCInspectionItem(BaseModel):
    """IPQC检验结果明细表"""
    __tablename__ = "ipqc_inspection_items"
    __table_args__ = (
        Index("idx_ipqc_items_inspection_id", "ipqc_inspection_id"),
        Index("idx_ipqc_items_item_no", "item_no"),
        {"schema": "quality"},
    )

    ipqc_inspection_id: Mapped[UUID] = mapped_column(ForeignKey("quality.ipqc_inspections.id"), nullable=False)
    item_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="项次")

    # 检验项目
    inspection_item: Mapped[str] = mapped_column(String(128), nullable=False, comment="检验项目名称")
    inspection_method: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="检验方法")
    standard_value: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="标准值")
    upper_limit: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="上限")
    lower_limit: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="下限")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")

    # 检验结果
    measured_value: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="实测值")
    result: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单项判定：pass/fail/na")
    is_repeat_test: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否复测")
    repeat_times: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False, comment="复测次数")

    # 原始记录
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始数据记录")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    ipqc_inspection: Mapped["IPQCInspection"] = relationship(back_populates="items")


class IPQCApprovalRecord(BaseModel):
    """IPQC审批记录表"""
    __tablename__ = "ipqc_approval_records"
    __table_args__ = (
        Index("idx_ipqc_approval_inspection_id", "ipqc_inspection_id"),
        {"schema": "quality"},
    )

    ipqc_inspection_id: Mapped[UUID] = mapped_column(ForeignKey("quality.ipqc_inspections.id"), nullable=False)
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False, comment="审批级别：1-车间工艺负责人，2-QC主管复核，3-QA终审")
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, comment="审批状态：pending/approved/rejected")
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
    ipqc_inspection: Mapped["IPQCInspection"] = relationship(back_populates="approval_records")
