"""AI 交互日志模型

记录所有 AI 调用交互日志，包括请求参数、响应结果、耗时等信息。
使用单独的 schema: qms_ai_log
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """AI 模块独立的 Base 类"""
    pass


class QmsAiLog(Base):
    """AI 交互日志表

    记录系统内所有 AI 能力调用日志，支持审计追溯和调用分析。
    """
    __tablename__ = "qms_ai_log"
    __table_args__ = {"schema": "qms"}

    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # 业务关联字段
    bill_no: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="关联单据编号",
    )
    operate_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="操作类型：如 试剂领用辅助、试剂报废辅助",
    )
    operator: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="操作人账号",
    )

    # AI 请求信息
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="系统提示词",
    )
    user_input: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="用户输入内容",
    )

    # AI 响应信息
    ai_response: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="AI 返回内容",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )

    # 调用统计
    tokens_used: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="使用的 token 数量",
    )
    latency_ms: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="响应耗时（毫秒）",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间",
    )