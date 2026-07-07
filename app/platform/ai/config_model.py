"""AI 系统配置模型

提供 AI 配置的数据库持久化存储。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for AI models"""
    pass


class QmsAiConfig(Base):
    """AI 系统配置表

    存储 AI 能力的配置信息，支持持久化存储和运行时更新。
    """
    __tablename__ = "qms_ai_config"
    __table_args__ = {"schema": "qms"}

    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # 配置键
    config_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="配置键",
    )

    # 配置值（JSON 格式存储复杂配置）
    config_value: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="配置值",
    )

    # 描述
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="配置描述",
    )

    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )