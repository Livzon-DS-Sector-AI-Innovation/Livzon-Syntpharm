"""SOP AI 模块 ORM 模型

定义三张数据库表：
- sop_ai_config: 配置表
- sop_ai_check_main: 校验主表
- sop_ai_check_problem: 问题明细表
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, Enum, ForeignKey, Index, Boolean, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, BaseModel


class CheckStatus(str, PyEnum):
    """校验状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CheckType(str, PyEnum):
    """校验类型枚举"""

    SINGLE = "single"  # 单文件预审
    BATCH = "batch"  # 批量巡检
    SCHEDULED = "scheduled"  # 定时任务


class FileType(str, PyEnum):
    """文件类型枚举"""

    DOC = "doc"
    DOCX = "docx"
    PDF = "pdf"
    TXT = "txt"


class RiskLevel(str, PyEnum):
    """风险等级枚举"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProblemType(str, PyEnum):
    """问题类型枚举"""

    DUPLICATE = "duplicate"  # 重复文件
    CONFLICT = "conflict"  # 参数冲突
    COMPLIANCE = "compliance"  # 合规问题
    FORMAT = "format"  # 格式问题
    CONTENT = "content"  # 内容问题


class HandleStatus(str, PyEnum):
    """问题处理状态枚举"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    IGNORED = "ignored"
    FIXED = "fixed"


class SopAiConfig(BaseModel):
    """SOP AI 配置表

    存储模块的配置项，如 SimHash 阈值、AI 提示词等。
    """

    __tablename__ = "sop_ai_config"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<SopAiConfig {self.config_key}>"


class SopAiCheckMain(Base):
    """SOP AI 校验主表

    存储每次校验任务的元信息和汇总结果。
    """

    __tablename__ = "sop_ai_check_main"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=None
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=None
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    file_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    check_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=CheckStatus.PENDING.value)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_problems: Mapped[int] = mapped_column(Integer, default=0)
    risk_high: Mapped[int] = mapped_column(Integer, default=0)
    risk_medium: Mapped[int] = mapped_column(Integer, default=0)
    risk_low: Mapped[int] = mapped_column(Integer, default=0)
    operator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 关联问题明细
    problems: Mapped[list["SopAiCheckProblem"]] = relationship(
        "SopAiCheckProblem",
        back_populates="main_record",
        cascade="all, delete-orphan",
    )

    # 索引
    __table_args__ = (
        Index("ix_sop_ai_check_main_status", "status"),
        Index("ix_sop_ai_check_main_file_code", "file_code"),
        Index("ix_sop_ai_check_main_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SopAiCheckMain {self.id} {self.file_name}>"


class SopAiCheckProblem(BaseModel):
    """SOP AI 问题明细表

    存储校验过程中发现的各类问题。
    """

    __tablename__ = "sop_ai_check_problem"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    main_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sop_ai_check_main.id"), nullable=False
    )
    problem_type: Mapped[Optional[str]] = mapped_column(
        Enum(ProblemType), nullable=True
    )
    risk_level: Mapped[Optional[str]] = mapped_column(
        Enum(RiskLevel), nullable=True
    )
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handle_status: Mapped[str] = mapped_column(
        Enum(HandleStatus), nullable=False, default=HandleStatus.PENDING
    )
    ignore_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 关联主记录
    main_record: Mapped["SopAiCheckMain"] = relationship(
        "SopAiCheckMain", back_populates="problems"
    )

    # 索引
    __table_args__ = (
        Index("ix_sop_ai_check_problem_main_id", "main_id"),
        Index("ix_sop_ai_check_problem_risk_level", "risk_level"),
        Index("ix_sop_ai_check_problem_handle_status", "handle_status"),
    )

    def __repr__(self) -> str:
        return f"<SopAiCheckProblem {self.id} {self.problem_type}>"