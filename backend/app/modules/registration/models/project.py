"""Registration project ORM model."""

import uuid
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel

# 申报前阶段（受理为界，"已受理"阶段只能由申报进度查询侧同步置达）
PRE_STAGES = ("initiation", "data_preparation", "internal_review", "submission", "accepted")


class RegistrationProject(BaseModel):
    """注册项目表"""

    __tablename__ = "registration_projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'preparing', 'submitted', 'accepted', "
            "'under_review', 'supplementary', 'approved', 'withdrawn', 'terminated')",
            name="ck_registration_projects_status",
        ),
        CheckConstraint(
            "pre_stage IN ('initiation', 'data_preparation', 'internal_review', 'submission', 'accepted')",
            name="ck_registration_projects_pre_stage",
        ),
        UniqueConstraint("project_no", name="uq_registration_projects_project_no"),
        {"schema": "registration"},
    )

    drug_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("registration.drugs.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联审评品种ID",
    )
    project_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="项目编号（留空自动生成）")
    name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="项目名称")
    product_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="品种名称")
    market: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="注册市场/国家")
    registration_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="注册类型（新注册/再注册/变更/补充申请）"
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="draft",
        comment="状态：draft/preparing/submitted/accepted/under_review/supplementary/approved/withdrawn/terminated",
    )
    pre_stage: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="initiation",
        comment="申报前阶段：initiation/data_preparation/internal_review/submission/accepted",
    )
    stage_completed_at: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="各申报前阶段完成时间 {stage: ISO8601 时间}",
    )
    planned_submission_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="预计递交日期")
    acceptance_number: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="受理号（受理后同步）")
    submitted_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="申报日期")
    accepted_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="受理日期")
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="获批日期")
    expected_completion_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="预计完成时间")
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="负责人")
    latest_progress: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最新进展")


class ProjectProgressLog(BaseModel):
    """注册项目进展记录表（审计追踪：只增不删不改，不提供更新/删除接口）"""

    __tablename__ = "project_progress_logs"
    __table_args__ = (
        CheckConstraint("log_type IN ('manual', 'system')", name="ck_project_progress_logs_type"),
        Index("ix_project_progress_logs_project", "project_id"),
        {"schema": "registration"},
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registration.registration_projects.id"),
        nullable=False,
        comment="所属注册项目ID",
    )
    log_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="记录类型：manual=手动 / system=系统自动")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="记录内容")
    # 覆盖为 Python 侧默认值：同事务内 Postgres now() 恒定，无法保证时间线倒序稳定
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")),
        server_default=func.now(),
    )
