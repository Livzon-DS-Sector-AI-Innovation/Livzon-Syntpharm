"""Quality ORM models live here."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class MaterialCategory(str, PyEnum):
    """物料分类"""

    RAW_MATERIAL = "raw_material"  # 原料
    EXCIPIENT = "excipient"  # 辅料
    PACKAGING_MATERIAL = "packaging_material"  # 包装材料
    INTERMEDIATE = "intermediate"  # 中间体
    FINISHED_PRODUCT = "finished_product"  # 原料药成品


class Pharmacopeia(str, PyEnum):
    """执行药典"""

    CHP = "ChP"  # 中国药典
    USP = "USP"  # 美国药典
    EP = "EP"  # 欧洲药典
    BP = "BP"  # 英国药典
    INTERNAL = "internal"  # 企业内控


class StandardStatus(str, PyEnum):
    """标准状态"""

    DRAFT = "draft"  # 草稿
    TECH_REVIEW = "tech_review"  # 技术部门审核
    QA_REVIEW = "qa_review"  # QA审核
    APPROVED = "approved"  # 已批准
    EFFECTIVE = "effective"  # 已生效
    OBSOLETE = "obsolete"  # 已作废
    REJECTED = "rejected"  # 已驳回


class LimitType(str, PyEnum):
    """限度类型"""

    UPPER_LIMIT = "upper_limit"  # 上限
    LOWER_LIMIT = "lower_limit"  # 下限
    RANGE = "range"  # 区间
    NOT_DETECTABLE = "not_detectable"  # 不得检出


class ItemCategory(str, PyEnum):
    """项目分类"""

    PHYSICAL_CHEMICAL = "physical_chemical"  # 理化
    RELATED_SUBSTANCES = "related_substances"  # 有关物质
    RESIDUAL_SOLVENTS = "residual_solvents"  # 残留溶剂
    MICROBIAL = "microbial"  # 微生物


class ApprovalStatus(str, PyEnum):
    """审批状态"""

    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已驳回


class InspectionStandard(BaseModel):
    """检验标准主表"""

    __tablename__ = "inspection_standards"
    __table_args__ = (
        UniqueConstraint("material_code", "version", name="uq_standards_material_version"),
        {"schema": "quality"},
    )

    standard_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="标准编号")
    material_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="物料编码")
    material_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="物料名称")
    cas_no: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="CAS号")
    material_category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="物料分类",
    )
    pharmacopeia: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="执行药典")
    version: Mapped[str] = mapped_column(String(20), nullable=False, comment="版本号")
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        server_default="draft",
        nullable=False,
        comment="状态",
    )
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="生效日期")
    obsolete_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="作废日期")
    is_obsolete: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否作废")
    obsolete_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="作废原因")
    sop_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="SOP编号")
    attachment_urls: Mapped[str | None] = mapped_column(Text, nullable=True, comment="附件URLs(JSON)")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    source_version: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="源版本号(复制用)")

    # 关系
    items: Mapped[list["InspectionStandardItem"]] = relationship(
        "InspectionStandardItem", back_populates="standard", lazy="selectin"
    )
    approval_records: Mapped[list["StandardApprovalRecord"]] = relationship(
        "StandardApprovalRecord", back_populates="standard", lazy="selectin"
    )


class InspectionStandardItem(BaseModel):
    """检验项目明细表"""

    __tablename__ = "inspection_standard_items"
    __table_args__ = {"schema": "quality"}

    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quality.inspection_standards.id"), nullable=False, comment="标准ID"
    )
    item_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="项目序号")
    item_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称")
    test_method: Mapped[str | None] = mapped_column(Text, nullable=True, comment="检测方法")
    instrument_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联仪器编号")
    reference_materials: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="所需对照品/试液")
    limit_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="限度类型")
    limit_value: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="合格限值")
    item_category: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="项目分类")
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否关键项目")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 关系
    standard: Mapped["InspectionStandard"] = relationship("InspectionStandard", back_populates="items")


class StandardApprovalRecord(BaseModel):
    """标准审批记录表"""

    __tablename__ = "standard_approval_records"
    __table_args__ = {"schema": "quality"}

    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quality.inspection_standards.id"), nullable=False, comment="标准ID"
    )
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False, comment="审批层级(1-技术/2-QA/3-质量负责人)")
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, comment="审批状态")
    approver_role: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="审批人角色")
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True, comment="审批人ID"
    )
    approver_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="审批人姓名")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="审批时间")
    comments: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审批意见")

    # 关系
    standard: Mapped["InspectionStandard"] = relationship("InspectionStandard", back_populates="approval_records")