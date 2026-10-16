"""CAPA (Corrective and Preventive Action) data models"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class CapaSource(StrEnum):
    """CAPA 来源"""

    DEVIATION = "deviation"  # 偏差
    AUDIT = "audit"  # 审计
    CUSTOMER_COMPLAINT = "customer_complaint"  # 客户投诉
    INTERNAL_INSPECTION = "internal_inspection"  # 内部检查


class CapaCategory(StrEnum):
    """CAPA 类别"""

    A = "A"  # A类
    B = "B"  # B类
    C = "C"  # C类


class CapaWorkflowStatus(StrEnum):
    """CAPA 工作流状态"""

    DRAFT = "draft"  # 草稿
    PART_A = "part_a"  # A部分（根本原因分析）
    PART_B = "part_b"  # B部分（CAPA计划）
    PART_C = "part_c"  # C部分（执行与验证）
    PENDING_DEPT_HEAD_CONFIRM = "pending_dept_head_confirm"  # 待部门负责人确认
    PENDING_QA_REVIEW = "pending_qa_review"  # 待QA审核
    PENDING_Q_HEAD_APPROVAL = "pending_q_head_approval"  # 待质量负责人批准
    EXECUTING = "executing"  # 执行中
    PENDING_EVALUATION = "pending_evaluation"  # 待评估
    SUBMITTED = "submitted"  # 已提交
    UNDER_EXECUTION = "under_execution"  # 执行中
    EVALUATION = "evaluation"  # 评估中
    CLOSED = "closed"  # 已关闭
    RETURNED = "returned"  # 已退回
    CANCELLED = "cancelled"  # 已取消


class Capa(BaseModel):
    """CAPA 主表"""

    __tablename__ = "capas"
    __table_args__ = (
        Index("idx_capa_code", "capa_code", unique=True),
        Index("idx_capa_status", "status"),
        Index("idx_capa_deviation_id", "deviation_id"),
        {"schema": "quality"},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capa_code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    final_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CapaWorkflowStatus] = mapped_column(
        String(50), nullable=False, default=CapaWorkflowStatus.DRAFT, server_default="draft"
    )

    # 关联信息
    deviation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quality.quality_deviations.id"), nullable=True
    )
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    root_cause_category: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 描述与分析
    non_conformity_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_attachments: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    reason_category: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # CAPA 内容
    capa_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    capa_items: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    executors: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    expected_completion_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # QA 审核
    qa_reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    qa_review_opinion: Mapped[str | None] = mapped_column(Text, nullable=True)
    qa_review_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 质量负责人批准
    q_head_approver_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    q_head_approval_opinion: Mapped[str | None] = mapped_column(Text, nullable=True)
    q_head_approval_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 执行跟踪
    execution_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_tracks: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    # 部门负责人确认
    dept_head_confirmations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    # 评估
    evaluation_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_target: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluation_confirmer_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    evaluation_confirm_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 关闭
    closure_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closure_remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 报告
    report_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_versions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # 工作流
    returned_step: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 报告人与QA确认
    reporter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qa_confirmer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qa_confirm_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
