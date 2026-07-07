"""FQC (Finished Product Quality Control) inspection models"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class FQCInspection(BaseModel):
    """FQC检验主表 - 成品检验"""
    __tablename__ = "fqc_inspections"
    __table_args__ = (
        Index("idx_fqc_inspection_no", "inspection_no", unique=True),
        Index("idx_fqc_batch_record_id", "batch_record_id"),
        Index("idx_fqc_batch_no", "batch_no"),
        Index("idx_fqc_product_code", "product_code"),
        Index("idx_fqc_status", "status"),
        Index("idx_fqc_inspection_date", "inspection_date"),
        Index("idx_fqc_release_status", "release_status"),
        {"schema": "quality"},
    )

    # 单据关联
    batch_record_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="关联批生产记录ID")
    batch_record_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="批生产记录编号")
    batch_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="成品生产批号")
    product_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="成品物料编码")
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="产品名称")
    sampling_order_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="入库取样单ID")
    sampling_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="入库取样单号")
    batch_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True, comment="批量")
    production_workshop: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="生产车间")

    # 基础信息
    cas_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="CAS号")
    manufacturing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="生产日期")
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="有效期至")
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="生产厂家")
    specification: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="产品规格/包装")

    # 检验信息
    inspection_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="检验单号")
    inspection_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="检验日期")
    inspector_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True, comment="检验员ID")
    inspector_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="检验员")

    # 质量标准
    standard_id: Mapped[UUID | None] = mapped_column(ForeignKey("quality.inspection_standards.id"), nullable=True, comment="检验标准ID")
    standard_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="质量标准名称")
    standard_version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="标准版本")

    # 检验结论
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False, comment="状态：draft/submitted/qc_supervisor_approved/qa_approved/final_approved/released/locked/closed")
    inspection_conclusion: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="检验结论：qualified/unqualified")
    conclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结论说明")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # OOS与偏差
    oos_report_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="OOS报告编号")
    deviation_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="关联偏差ID")

    # 批次状态
    batch_locked: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="批次是否锁定")
    batch_lock_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="批次锁定原因")
    warehouse_isolation: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否入库隔离")

    # 放行状态
    release_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="放行状态：pending_release/released/not_released")
    release_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="放行说明")

    # 复检
    reinspection_applied: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否申请复检")
    reinspection_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="复检原因")

    # 附件
    attachments: Mapped[str | None] = mapped_column(Text, nullable=True, comment="附件JSON")

    # 检验报告
    report_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="检验报告书编号")
    report_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="检验报告书URL")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    items: Mapped[list["FQCInspectionItem"]] = relationship(back_populates="fqc_inspection", lazy="selectin")
    approval_records: Mapped[list["FQCApprovalRecord"]] = relationship(back_populates="fqc_inspection", lazy="selectin")


class FQCInspectionItem(BaseModel):
    """FQC检验结果明细表"""
    __tablename__ = "fqc_inspection_items"
    __table_args__ = (
        Index("idx_fqc_items_inspection_id", "fqc_inspection_id"),
        Index("idx_fqc_items_item_no", "item_no"),
        {"schema": "quality"},
    )

    fqc_inspection_id: Mapped[UUID] = mapped_column(ForeignKey("quality.fqc_inspections.id"), nullable=False)
    item_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="项次")
    inspection_category: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="检验类别")

    # 检验项目
    inspection_item: Mapped[str] = mapped_column(String(128), nullable=False, comment="检验项目名称")
    inspection_method: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="检验方法")
    standard_value: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="标准值/限度")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")

    # 检验结果
    measured_value: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="实测值")
    result: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单项判定：pass/fail/na")
    is_oos: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否超标")
    oos_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="超标描述")
    is_repeat_test: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否复测")
    repeat_times: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False, comment="复测次数")

    # 附件
    chromatogram_urls: Mapped[str | None] = mapped_column(Text, nullable=True, comment="图谱附件JSON")
    raw_record_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="原始记录PDF URL")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    fqc_inspection: Mapped["FQCInspection"] = relationship(back_populates="items")


class FQCApprovalRecord(BaseModel):
    """FQC审批记录表"""
    __tablename__ = "fqc_approval_records"
    __table_args__ = (
        Index("idx_fqc_approval_inspection_id", "fqc_inspection_id"),
        {"schema": "quality"},
    )

    fqc_inspection_id: Mapped[UUID] = mapped_column(ForeignKey("quality.fqc_inspections.id"), nullable=False)
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False, comment="审批级别：1-QC主管，2-QA，3-质量负责人")
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
    fqc_inspection: Mapped["FQCInspection"] = relationship(back_populates="approval_records")
