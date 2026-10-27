"""提醒配置表 ORM 模型（迁移 0086 建表，现有代码用原生 SQL 读写）。

这两张是「配置表」，物理表没有 `BaseModel` 的审计列（`created_by` / `updated_by`），
所以直接继承 `Base` 而不是 `BaseModel`：模型的作用只是让 `alembic check` /
`autogenerate` 能看见它们（此前靠 `env.py` 的 `RAW_SQL_ONLY_TABLES` 白名单遮蔽，
字段漂移永远发现不了）。读写路径保持原样，不为了建模去改表结构。
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base


class QmsReagentItemReminderConfig(Base):
    """试剂按名称的提醒开关（`qms.qms_reagent_item_reminder_config`）。"""

    __tablename__ = "qms_reagent_item_reminder_config"
    __table_args__ = (
        Index("ix_qms_reagent_item_reminder_config_reagent_name", "reagent_name", unique=True),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reagent_name: Mapped[str] = mapped_column(String(255))
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class QmsDeviationReminderRule(Base):
    """偏差填报人提醒规则（`qms.qms_deviation_reminder_rules`）。"""

    __tablename__ = "qms_deviation_reminder_rules"
    __table_args__ = {"schema": "qms"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviation_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    urgency_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    auto_reminder: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    reminder_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    message_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
