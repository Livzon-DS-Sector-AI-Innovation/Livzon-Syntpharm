"""IQC (Incoming Quality Control) inspection models"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class IQCInspection(BaseModel):
    """IQC检验主表"""
    __tablename__ = "iqc_inspections"
    __table_args__ = (
        Index("idx_iqc_inspection_no", "inspection_no", unique=True),
        Index("idx_iqc_sampling_order_id", "sampling_order_id"),
        Index("idx_iqc_source_no", "source_no"),
        Index("idx_iqc_material_code", "material_code"),
        Index("idx_iqc_supplier_code", "supplier_code"),
        Index("idx_iqc_status", "status"),
        Index("idx_iqc_inspection_date", "inspection_date"),
        {"schema": "quality"},
    )

    # 单据信息
    inspection_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="检验单号")
    sampling_order_id: Mapped[UUID | None] = mapped_column(ForeignKey("quality.sampling_orders.id"), nullable=True, comment="关联取样单ID")
    sampling_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联取样单号")

    # 来源信息
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="来源类型：purchase_inbound/supplier_delivery")
    source_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源单号（如采购到货单号）")

    # 物料信息
    material_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="物料编码")
    material_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="物料名称")
    material_category: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="物料类别：raw_material/excipient/packaging_material")
    specification: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="规格")
    batch_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="批次号")
    supplier_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="供应商编码")
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="供应商名称")
    manufacturing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="生产日期")
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="有效期")
    quantity_received: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True, comment="到货数量")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")

    # 检验信息
    inspection_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="检验日期")
    inspector_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True, comment="检验员ID")
    inspector_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="检验员姓名")

    # 质量标准
    standard_id: Mapped[UUID | None] = mapped_column(ForeignKey("quality.inspection_standards.id"), nullable=True, comment="检验标准ID")
    standard_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="检验标准名称")
    standard_version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="标准版本")

    # 检验结论
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False, comment="状态：draft/submitted/department_approved/qa_approved/final_approved/rejected")
    inspection_conclusion: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="检验结论：qualified/unqualified/conditional")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    deviation_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="关联偏差ID")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    items: Mapped[list["IQCInspectionItem"]] = relationship(back_populates="iqc_inspection", lazy="selectin")
    approval_records: Mapped[list["IQCApprovalRecord"]] = relationship(back_populates="iqc_inspection", lazy="selectin")


class IQCInspectionItem(BaseModel):
    """IQC检验结果明细表"""
    __tablename__ = "iqc_inspection_items"
    __table_args__ = (
        Index("idx_iqc_items_inspection_id", "iqc_inspection_id"),
        Index("idx_iqc_items_item_no", "item_no"),
        {"schema": "quality"},
    )

    iqc_inspection_id: Mapped[UUID] = mapped_column(ForeignKey("quality.iqc_inspections.id"), nullable=False)
    item_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="项次")

    # 检验项目
    inspection_item: Mapped[str] = mapped_column(String(128), nullable=False, comment="检验项目名称")
    inspection_method: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="检验方法")
    standard_value: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="标准值")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")

    # 检验结果
    measured_value: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="实测值")
    result: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单项判定：pass/fail/na")
    is_repeat_test: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否复测")

    # 原始记录
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始数据记录")

    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    iqc_inspection: Mapped["IQCInspection"] = relationship(back_populates="items")


class IQCApprovalRecord(BaseModel):
    """IQC审批记录表"""
    __tablename__ = "iqc_approval_records"
    __table_args__ = (
        Index("idx_iqc_approval_inspection_id", "iqc_inspection_id"),
        {"schema": "quality"},
    )

    iqc_inspection_id: Mapped[UUID] = mapped_column(ForeignKey("quality.iqc_inspections.id"), nullable=False)
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False, comment="审批级别：1-部门负责人，2-QA，3-质量负责人")
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
    iqc_inspection: Mapped["IQCInspection"] = relationship(back_populates="approval_records")