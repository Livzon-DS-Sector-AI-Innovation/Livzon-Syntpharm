"""偏差流程表 ORM 模型（迁移 0093 建表，现有代码用原生 SQL 读写）。

这四张表由 `deviation_flow_api.py` / `deviation_reporter_reminder_service.py` /
`deviation_settings_api.py` 的原生 SQL 直接读写，物理表沿用历史结构、没有
`BaseModel` 的审计列（`created_by` / `updated_by`），所以直接继承 `Base` 而不是
`BaseModel`：模型的作用只是让 `alembic check` / `autogenerate` 能看见它们，避免
「代码里在读写、迁移体系里不存在」的漂移（此前 `qms.qms_deviation` 等表就是这种
状态，端点挂载后一调即 `UndefinedTable`）。读写路径保持原样。

时间列统一使用不带时区的 `timestamp`：上游代码用 `datetime.now()` 做倒计时与提醒
天数计算，若列带时区会拿到 aware datetime，与 naive now 相减直接 `TypeError`。
"""

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Index, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base


class QmsDeviation(Base):
    """偏差单主表（`qms.qms_deviation`）。"""

    __tablename__ = "qms_deviation"
    __table_args__ = (
        Index("ix_qms_deviation_deviation_no", "deviation_no"),
        Index("ix_qms_deviation_status", "status"),
        Index("ix_qms_deviation_created_at", "created_at"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviation_no: Mapped[str] = mapped_column(String(64), nullable=False)
    theme: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    discovered_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    responsible_department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    occurred_area: Mapped[str | None] = mapped_column(String(200), nullable=True)
    deviation_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    urgency_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))

    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    equipment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    standard_based_on: Mapped[str | None] = mapped_column(Text, nullable=True)
    deviation_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)

    temp_measures: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_deviation_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_capa: Mapped[str | None] = mapped_column(Text, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    qa_feishu_open_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    qa_feishu_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dept_leader_feishu_open_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dept_leader_feishu_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    reporter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reporter_department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reporter_feishu_open_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    report_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)


class QmsDeviationAttachment(Base):
    """偏差附件（`qms.qms_deviation_attachment`）。"""

    __tablename__ = "qms_deviation_attachment"
    __table_args__ = (
        Index("ix_qms_deviation_attachment_deviation_id", "deviation_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviation_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_report: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class QmsDeviationLog(Base):
    """偏差操作日志（`qms.qms_deviation_log`）。"""

    __tablename__ = "qms_deviation_log"
    __table_args__ = (
        Index("ix_qms_deviation_log_deviation_id", "deviation_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviation_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operator_department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class QmsDeviationFeishuBotConfig(Base):
    """偏差流程飞书机器人配置（`qms.qms_deviation_feishu_bot_config`）。"""

    __tablename__ = "qms_deviation_feishu_bot_config"
    __table_args__ = ({"schema": "qms"},)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    app_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    app_secret: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bot_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    encrypt_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    verification_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), nullable=True)


class QmsDeviationAutoTrigger(Base):
    """偏差自动提醒触发配置（`qms.qms_deviation_auto_trigger`）。"""

    __tablename__ = "qms_deviation_auto_trigger"
    __table_args__ = (Index("ix_qms_deviation_auto_trigger_type", "trigger_type"), {"schema": "qms"})

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    notify_qa: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    notify_leader: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    notify_reporter: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    custom_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)


class QmsDeviationMessageTemplate(Base):
    """偏差消息模板（`qms.qms_deviation_message_template`）。"""

    __tablename__ = "qms_deviation_message_template"
    __table_args__ = (
        Index("ix_qms_deviation_message_template_type", "template_type"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_type: Mapped[str] = mapped_column(String(64), nullable=False)
    template_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), nullable=True)
