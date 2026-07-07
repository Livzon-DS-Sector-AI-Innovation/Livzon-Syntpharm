"""偏差管理数据模型"""

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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class DeviationType(str, Enum):
    """偏差类型"""
    IPC_DEFECT = "ipc_defect"                       # 过程控制（IPC）缺陷
    FOREIGN_OBJECT = "foreign_object"               # 外来异物（有形）
    CALIBRATION_MAINTENANCE = "calibration_maintenance"  # 校验/预防维修
    MIXUP = "mixup"                                 # 混淆
    MATERIAL_QUALITY_DEFECT = "material_quality_defect"  # 物料质量缺陷
    PERSONNEL_ERROR = "personnel_error"             # 人员失误
    OOS_RESULT = "oos_result"                       # 超标检验结果
    DOCUMENTATION_DEFECT = "documentation_defect"   # 文件记录缺陷
    EQUIPMENT_FAILURE = "equipment_failure"         # 设备故障/过程中断
    ENVIRONMENT = "environment"                     # 环境
    OTHER = "other"                                 # 其它


class DeviationLevel(str, Enum):
    """偏差等级"""
    CRITICAL = "critical"   # 重大
    MAJOR = "major"         # 主要
    MINOR = "minor"         # 次要


class DeviationStatus(str, Enum):
    """偏差状态"""
    DRAFT = "draft"               # 草稿
    SUBMITTED = "submitted"        # 已提交
    ADMIN_APPROVED = "admin_approved"    # 部门负责人已审核
    QA_APPROVED = "qa_approved"          # QA已审核
    QUALITY_APPROVED = "quality_approved" # 质量负责人已审核
    ACTIVE = "active"             # 已启用/调查中
    INVESTIGATING = "investigating"  # 调查中
    INVESTIGATION_COMPLETED = "investigation_completed"  # 调查完成
    CORRECTION_PENDING = "correction_pending"  # 待整改
    CORRECTION_IN_PROGRESS = "correction_in_progress"  # 整改中
    CORRECTION_COMPLETED = "correction_completed"  # 整改完成
    CLOSING_PENDING = "closing_pending"  # 待关闭
    CLOSED = "closed"             # 已关闭
    REJECTED = "rejected"         # 已驳回


class InvestigationStatus(str, Enum):
    """调查状态"""
    PENDING = "pending"           # 待调查
    IN_PROGRESS = "in_progress"   # 调查中
    COMPLETED = "completed"       # 已完成


class CorrectionStatus(str, Enum):
    """整改状态"""
    PENDING = "pending"           # 待整改
    IN_PROGRESS = "in_progress"   # 整改中
    COMPLETED = "completed"       # 已完成


class BatchLockStatus(str, Enum):
    """批次锁定状态"""
    LOCKED = "locked"            # 已锁定
    UNLOCKED = "unlocked"         # 已解锁


class Deviation(BaseModel):
    """偏差主表"""
    __tablename__ = 'quality_deviations'
    __table_args__ = (
        Index('idx_deviation_no', 'deviation_no', unique=True),
        Index('idx_deviation_status', 'status'),
        Index('idx_deviation_type', 'deviation_type'),
        Index('idx_deviation_level', 'deviation_level'),
        Index('idx_occurrence_date', 'occurrence_date'),
        {"schema": "quality"},
    )

    # 偏差编号（系统自动生成）
    deviation_no: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment='偏差编号'
    )

    # 发生信息
    occurrence_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment='发生日期'
    )
    discovering_department: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment='发现部门'
    )
    discoverer: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment='发现人'
    )

    # 涉及产品信息
    product_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment='产品编码'
    )
    product_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment='产品名称'
    )
    production_batch: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment='生产批次'
    )
    material_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment='物料编码'
    )
    batch_size: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment='批量'
    )

    # 分类
    deviation_type: Mapped[str] = mapped_column(
        SQLEnum(DeviationType, name='deviation_type_enum', create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, comment='偏差类型'
    )
    deviation_level: Mapped[str] = mapped_column(
        SQLEnum(DeviationLevel, name='deviation_level_enum', create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, comment='偏差等级'
    )

    # 偏差描述
    abnormal_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='异常现象描述'
    )
    impact_scope: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='影响范围'
    )
    emergency_measures: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='已执行临时应急措施'
    )

    # 附件（JSON数组存储）
    attachments: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment='附件列表'
    )

    # 批次锁定
    batch_locked: Mapped[bool] = mapped_column(
        Boolean, default=False, comment='批次是否锁定'
    )
    batch_lock_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='锁定原因'
    )
    batch_locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment='锁定时间'
    )

    # 状态
    status: Mapped[str] = mapped_column(
        SQLEnum(DeviationStatus, name='deviation_status_enum', create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DeviationStatus.DRAFT, comment='状态'
    )

    # 关联调查、整改、关闭
    investigation: Mapped[Optional["DeviationInvestigation"]] = relationship(
        "DeviationInvestigation", back_populates="deviation", uselist=False
    )
    correction: Mapped[Optional["DeviationCorrection"]] = relationship(
        "DeviationCorrection", back_populates="deviation", uselist=False
    )
    closing: Mapped[Optional["DeviationClosing"]] = relationship(
        "DeviationClosing", back_populates="deviation", uselist=False
    )
    approvals: Mapped[list["DeviationApproval"]] = relationship(
        "DeviationApproval", back_populates="deviation"
    )


class DeviationInvestigation(BaseModel):
    """偏差调查表"""
    __tablename__ = 'quality_deviation_investigations'
    __table_args__ = (
        Index('idx_investigation_deviation', 'deviation_id'),
        {"schema": "quality"},
    )

    deviation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('quality.quality_deviations.id'),
        nullable=False, comment='关联偏差ID'
    )

    # 调查信息
    investigation_team: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment='调查小组'
    )
    investigation_start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment='调查开始日期'
    )
    investigation_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment='调查结束日期'
    )
    investigation_method: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment='调查方式'
    )

    # 原因分析
    direct_cause: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='直接原因'
    )
    indirect_cause: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='间接原因'
    )
    root_cause: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='根本原因'
    )
    why_analysis: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='5Why分析内容'
    )

    # 影响评估
    impact_assessment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='影响评估'
    )
    investigation_conclusion: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='调查结论'
    )
    affected_batches: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='受影响批次范围'
    )
    temporary_measures: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='阶段性临时措施'
    )

    # 附件
    attachments: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment='附件（鱼骨图、分析报告等）'
    )

    # 状态
    status: Mapped[str] = mapped_column(
        SQLEnum(InvestigationStatus, name='investigation_status_enum', create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=InvestigationStatus.PENDING, comment='调查状态'
    )

    # 关联
    deviation: Mapped["Deviation"] = relationship(
        "Deviation", back_populates="investigation"
    )


class DeviationCorrection(BaseModel):
    """偏差整改表"""
    __tablename__ = 'quality_deviation_corrections'
    __table_args__ = (
        Index('idx_correction_deviation', 'deviation_id'),
        {"schema": "quality"},
    )

    deviation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('quality.quality_deviations.id'),
        nullable=False, comment='关联偏差ID'
    )

    # 整改责任人
    responsible_department: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment='责任部门'
    )
    responsible_person: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment='责任人'
    )
    plan_completion_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment='计划完成日期'
    )

    # 整改措施（合并CA+PA文本）
    correction_measures: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='整改措施（CA+PA）'
    )

    # 整改内容（JSON数组存储）
    temporary_corrective_actions: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment='临时纠正措施'
    )
    long_term_corrective_actions: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment='长期整改措施'
    )

    # 整改进度
    progress: Mapped[int] = mapped_column(
        Integer, default=0, comment='整改进度(0-100)'
    )
    status: Mapped[str] = mapped_column(
        SQLEnum(CorrectionStatus, name='correction_status_enum', create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CorrectionStatus.PENDING, comment='整改状态'
    )

    # 佐证材料
    evidence_attachments: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment='整改佐证材料'
    )

    # 关联
    deviation: Mapped["Deviation"] = relationship(
        "Deviation", back_populates="correction"
    )


class DeviationClosing(BaseModel):
    """偏差关闭表"""
    __tablename__ = 'quality_deviation_closings'
    __table_args__ = (
        Index('idx_closing_deviation', 'deviation_id'),
        {"schema": "quality"},
    )

    deviation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('quality.quality_deviations.id'),
        nullable=False, comment='关联偏差ID'
    )

    # 效果验证
    verification_plan: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='验证方案'
    )
    verification_data: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='验证数据'
    )
    verification_result: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='比对结果'
    )
    is_resolved: Mapped[bool] = mapped_column(
        Boolean, default=False, comment='问题是否彻底解决'
    )

    # 综合结论
    conclusion: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='综合结论'
    )

    # 附件
    attachments: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment='验证报告等附件'
    )

    # 批次解锁
    batch_unlocked: Mapped[bool] = mapped_column(
        Boolean, default=False, comment='批次是否已解锁'
    )

    # 归档
    archived: Mapped[bool] = mapped_column(
        Boolean, default=False, comment='是否已归档'
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment='归档时间'
    )

    # 关联
    deviation: Mapped["Deviation"] = relationship(
        "Deviation", back_populates="closing"
    )


class DeviationApproval(BaseModel):
    """偏差审批记录表"""
    __tablename__ = 'quality_deviation_approvals'
    __table_args__ = (
        Index('idx_approval_deviation', 'deviation_id'),
        {"schema": "quality"},
    )

    deviation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('quality.quality_deviations.id'),
        nullable=False, comment='关联偏差ID'
    )

    approval_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment='审批类型: submit/admin/qa/quality/investigation/correction/closing'
    )
    approver_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment='审批人姓名'
    )
    approver_department: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment='审批人部门'
    )
    approval_comments: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment='审批意见'
    )
    approved: Mapped[bool] = mapped_column(
        Boolean, nullable=True, comment='是否批准'
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment='审批时间'
    )

    # 关联
    deviation: Mapped["Deviation"] = relationship(
        "Deviation", back_populates="approvals"
    )