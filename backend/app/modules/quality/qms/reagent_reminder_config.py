"""试剂提醒配置数据模型

用于存储试剂库存不足时的飞书提醒配置
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class ReagentReminderConfig(BaseModel):
    """试剂提醒配置表"""

    __tablename__ = "qms_reagent_reminder_config"
    __table_args__ = {"schema": "qms", "comment": "试剂提醒配置表"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 飞书配置
    feishu_app_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="飞书应用 AppID")
    feishu_app_secret: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="飞书应用 AppSecret")
    feishu_chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="飞书群 ID")

    # 提醒规则
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=2, comment="库存不足阈值（默认2）")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用提醒")

    # 提醒历史
    last_remind_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="上次提醒时间")
    last_remind_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="上次提醒内容")

    # 状态
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="创建人")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="更新人")
    updated_at: Mapped[datetime | None] = mapped_column(  # type: ignore[assignment]
        DateTime, nullable=True, onupdate=datetime.utcnow, comment="更新时间"
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否删除")
