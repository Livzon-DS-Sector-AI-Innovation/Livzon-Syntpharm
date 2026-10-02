"""试剂提醒配置数据模型

用于存储试剂库存不足时的飞书提醒配置

继承共享 `app.shared.base_model.BaseModel`，标准契约由基类提供：
UUID `id`、`created_at`、`updated_at`、`created_by`、`updated_by`、`is_deleted`。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class ReagentReminderConfig(BaseModel):
    """试剂提醒配置表"""

    __tablename__ = "qms_reagent_reminder_config"
    __table_args__ = {"schema": "qms", "comment": "试剂提醒配置表"}

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
