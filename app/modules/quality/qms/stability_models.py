"""Stability Study (稳定性试验) models"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class StabilityStudy(BaseModel):
    """稳定性试验方案主表"""
    __tablename__ = "stability_studies"
    __table_args__ = (
        Index("idx_stability_study_no", "study_no", unique=True),
        Index("idx_stability_product_code", "product_code"),
        Index("idx_stability_batch_no", "batch_no"),
        Index("idx_stability_status", "status"),
        Index("idx_stability_study_type", "study_type"),
        {"schema": "quality"},
    )

    # 方案编号
    study_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="试验方案编号")

    # 产品信息
    product_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="产品编码")
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="产品名称")
    product_category: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="产品类别")

    # 批次信息
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="批号")
    batch_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True, comment="批量")
    packaging_spec: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="包装规格")

    # 试验条件
    study_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="试验类型")
    temperature: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="温度条件")
    humidity: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="湿度条件")

    # 试验周期
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="试验开始日期")
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="试验结束日期")
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="有效期")

    # 取样周期
    sample_intervals: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="取样周期节点")

    # 质量标准
    standard_id: Mapped[UUID | None] = mapped_column(ForeignKey("quality.inspection_standards.id"), nullable=True, comment="关联质量标准ID")
    standard_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="质量标准名称")
    standard_version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="标准版本")

    # 方案负责人
    developer_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True, comment="研发人员ID")
    developer_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="研发人员")

    # 状态
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False, comment="状态")

    # 方案结论
    study_conclusion: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="试验结论")
    conclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结论说明")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 附件
    attachments: Mapped[str | None] = mapped_column(Text, nullable=True, comment="附件JSON")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    sample_nodes: Mapped[list["StabilitySampleNode"]] = relationship(back_populates="stability_study", lazy="selectin")
    inspections: Mapped[list["StabilityInspection"]] = relationship(back_populates="stability_study", lazy="selectin")
    approval_records: Mapped[list["StabilityApprovalRecord"]] = relationship(
        foreign_keys="StabilityApprovalRecord.study_id",
        back_populates="stability_study",
        lazy="selectin"
    )


class StabilitySampleNode(BaseModel):
    """稳定性取样节点表"""
    __tablename__ = "stability_sample_nodes"
    __table_args__ = (
        Index("idx_sample_node_study_id", "stability_study_id"),
        Index("idx_sample_node_planned_date", "planned_date"),
        Index("idx_sample_node_status", "status"),
        {"schema": "quality"},
    )

    stability_study_id: Mapped[UUID] = mapped_column(ForeignKey("quality.stability_studies.id"), nullable=False, comment="稳定性试验ID")
    node_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="节点序号")
    node_month: Mapped[int] = mapped_column(Integer, nullable=False, comment="节点月数")
    node_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="节点名称")

    # 计划日期
    planned_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="计划取样日期")

    # 实际日期
    actual_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="实际取样日期")

    # 取样数量
    sample_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True, comment="取样数量")

    # 状态
    status: Mapped[str] = mapped_column(String(32), server_default="pending", nullable=False, comment="状态")

    # 预警状态
    reminder_sent: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否已发送预警")
    reminder_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="预警发送时间")

    # 检验记录（不使用外键约束，保留字段用于关联）
    inspection_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="关联检验记录ID")
    inspection_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="检验记录编号")
    inspection_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="检验状态")
    inspection_conclusion: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="检验结论")

    # 备注
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    stability_study: Mapped["StabilityStudy"] = relationship(back_populates="sample_nodes")


class StabilityInspection(BaseModel):
    """稳定性检验记录表"""
    __tablename__ = "stability_inspections"
    __table_args__ = (
        Index("idx_stability_inspection_no", "inspection_no", unique=True),
        Index("idx_stability_inspection_study_id", "study_id"),
        Index("idx_stability_inspection_node_id", "sample_node_id"),
        Index("idx_stability_inspection_status", "status"),
        {"schema": "quality"},
    )

    # 关联信息
    study_id: Mapped[UUID] = mapped_column(ForeignKey("quality.stability_studies.id"), nullable=False, comment="稳定性试验ID")
    study_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="试验方案编号")
    sample_node_id: Mapped[UUID] = mapped_column(ForeignKey("quality.stability_sample_nodes.id"), nullable=False, comment="取样节点ID")
    node_month: Mapped[int] = mapped_column(Integer, nullable=False, comment="节点月数")

    # 检验单号
    inspection_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="检验单号")

    # 产品信息
    product_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="产品编码")
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="产品名称")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="批号")
    specification: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="规格/包装")

    # 检验信息
    inspection_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="检验日期")
    inspector_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True, comment="检验员ID")
    inspector_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="检验员")

    # 取样信息
    sample_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True, comment="取样数量")
    sample_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="样品编号")
    sample_condition: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="样品状态")

    # 质量标准
    standard_id: Mapped[UUID | None] = mapped_column(ForeignKey("quality.inspection_standards.id"), nullable=True, comment="检验标准ID")
    standard_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="质量标准名称")

    # 检验结论
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False, comment="状态")
    inspection_conclusion: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="检验结论")
    conclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结论说明")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # OOS
    oos_report_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="OOS报告编号")
    is_oos: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否OOS")

    # 附件
    attachments: Mapped[str | None] = mapped_column(Text, nullable=True, comment="附件JSON")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    stability_study: Mapped["StabilityStudy"] = relationship(back_populates="inspections")
    sample_node: Mapped["StabilitySampleNode"] = relationship(foreign_keys=[sample_node_id])
    items: Mapped[list["StabilityInspectionItem"]] = relationship(back_populates="stability_inspection", lazy="selectin")
    approval_records: Mapped[list["StabilityApprovalRecord"]] = relationship(
        foreign_keys="StabilityApprovalRecord.inspection_id",
        lazy="selectin"
    )


class StabilityInspectionItem(BaseModel):
    """稳定性检验明细表"""
    __tablename__ = "stability_inspection_items"
    __table_args__ = (
        Index("idx_stability_items_inspection_id", "stability_inspection_id"),
        {"schema": "quality"},
    )

    stability_inspection_id: Mapped[UUID] = mapped_column(ForeignKey("quality.stability_inspections.id"), nullable=False, comment="稳定性检验ID")
    item_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="项次")
    inspection_item: Mapped[str] = mapped_column(String(128), nullable=False, comment="检验项目名称")
    inspection_method: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="检验方法")
    standard_value: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="标准值/限度")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")
    measured_value: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="实测值")
    result: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单项判定")
    is_oos: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否超标")
    oos_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="超标描述")

    # 趋势分析相关
    data_point: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="数据点")

    # 图谱附件
    chromatogram_urls: Mapped[str | None] = mapped_column(Text, nullable=True, comment="图谱附件JSON")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    stability_inspection: Mapped["StabilityInspection"] = relationship(back_populates="items")


class StabilityApprovalRecord(BaseModel):
    """稳定性审批记录表"""
    __tablename__ = "stability_approval_records"
    __table_args__ = (
        Index("idx_stability_approval_study_id", "study_id"),
        Index("idx_stability_approval_inspection_id", "inspection_id"),
        {"schema": "quality"},
    )

    study_id: Mapped[UUID | None] = mapped_column(ForeignKey("quality.stability_studies.id"), nullable=True, comment="稳定性试验ID")
    inspection_id: Mapped[UUID | None] = mapped_column(ForeignKey("quality.stability_inspections.id"), nullable=True, comment="检验记录ID")
    approval_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="审批类型")
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False, comment="审批级别")
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, comment="审批状态")
    approver_role: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="审批角色")
    approver_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    approver_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="审批人姓名")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="审批时间")
    comments: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审批意见")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # 关系
    stability_study: Mapped[Optional["StabilityStudy"]] = relationship(back_populates="approval_records")
    inspection: Mapped[Optional["StabilityInspection"]] = relationship(back_populates="approval_records")
