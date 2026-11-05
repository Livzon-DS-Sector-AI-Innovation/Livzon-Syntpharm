"""quality qms deviation flow tables

Revision ID: 0109_quality_qms_deviation_flow_tables
Revises: 0092_identity_revoked_sessions_comments_fks
Create Date: 2026-11-01

补齐质量模块偏差流程的四张表。代码中已有原生 SQL 直接读写这些表，但历史迁移
从未创建，导致以下接口在表不存在的库上一调即 `UndefinedTable`（HTTP 500）：

- GET/POST/PUT/DELETE /api/v1/quality/deviation-flow*
- GET/POST        /api/v1/quality/deviation-flow/{deviation_id}/attachments
- GET             /api/v1/quality/deviation-settings/message-templates
- 偏差提醒定时任务（deviation_reporter_reminder_service）

四张表沿用历史结构（无 `created_by` / `updated_by` 审计列），时间列使用不带时区的
`timestamp`，与上游 `datetime.now()` 的天数计算保持一致。

建表使用 `to_regclass` 幂等检查：部分环境（如历史 UAT 库）可能已手工建过同名表，
直接 `CREATE TABLE` 会失败。仅涉及 quality 模块 `qms` schema，符合单模块迁移原则。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0109_quality_qms_deviation_flow_tables"
down_revision: str = "0092_identity_revoked_sessions_comments_fks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    """判断 qms schema 下的表是否已存在（历史环境可能手工建过）。"""
    bind = op.get_bind()
    return bind.execute(sa.text("SELECT to_regclass(:fq_name)"), {"fq_name": f"qms.{table_name}"}).scalar() is not None


def upgrade() -> None:
    if not _table_exists("qms_deviation"):
        op.create_table(
            "qms_deviation",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("deviation_no", sa.String(64), nullable=False),
            sa.Column("theme", sa.String(255), nullable=True),
            sa.Column("occurred_date", sa.Date(), nullable=True),
            sa.Column("discovered_date", sa.Date(), nullable=True),
            sa.Column("responsible_department", sa.String(100), nullable=True),
            sa.Column("occurred_area", sa.String(200), nullable=True),
            sa.Column("deviation_type", sa.String(64), nullable=True),
            sa.Column("urgency_level", sa.String(32), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'draft'")),
            sa.Column("product_name", sa.String(255), nullable=True),
            sa.Column("batch_no", sa.String(64), nullable=True),
            sa.Column("equipment", sa.String(255), nullable=True),
            sa.Column("standard_based_on", sa.Text(), nullable=True),
            sa.Column("deviation_description", sa.Text(), nullable=True),
            sa.Column("risk_assessment", sa.Text(), nullable=True),
            sa.Column("temp_measures", sa.Text(), nullable=True),
            sa.Column("related_deviation_no", sa.String(64), nullable=True),
            sa.Column("related_capa", sa.Text(), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.Column("qa_feishu_open_id", sa.String(128), nullable=True),
            sa.Column("qa_feishu_name", sa.String(100), nullable=True),
            sa.Column("dept_leader_feishu_open_id", sa.String(128), nullable=True),
            sa.Column("dept_leader_feishu_name", sa.String(100), nullable=True),
            sa.Column("reporter", sa.String(100), nullable=True),
            sa.Column("reporter_department", sa.String(100), nullable=True),
            sa.Column("reporter_feishu_open_id", sa.String(128), nullable=True),
            sa.Column("report_time", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            schema="qms",
        )

    if not _table_exists("qms_deviation_attachment"):
        op.create_table(
            "qms_deviation_attachment",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("deviation_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("file_path", sa.String(512), nullable=False),
            sa.Column("file_type", sa.String(128), nullable=True),
            sa.Column("file_size", sa.BigInteger(), nullable=True),
            sa.Column("is_report", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            schema="qms",
        )

    if not _table_exists("qms_deviation_log"):
        op.create_table(
            "qms_deviation_log",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("deviation_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("action", sa.String(50), nullable=True),
            sa.Column("operator", sa.String(100), nullable=True),
            sa.Column("operator_department", sa.String(100), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            schema="qms",
        )

    if not _table_exists("qms_deviation_message_template"):
        op.create_table(
            "qms_deviation_message_template",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("template_type", sa.String(64), nullable=False),
            sa.Column("template_name", sa.String(255), nullable=True),
            sa.Column("title_template", sa.Text(), nullable=True),
            sa.Column("content_template", sa.Text(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            schema="qms",
        )

    if not _table_exists("qms_deviation_feishu_bot_config"):
        op.create_table(
            "qms_deviation_feishu_bot_config",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("bot_name", sa.String(100), nullable=True),
            sa.Column("app_id", sa.String(128), nullable=True),
            sa.Column("app_secret", sa.String(256), nullable=True),
            sa.Column("bot_token", sa.String(256), nullable=True),
            sa.Column("encrypt_key", sa.String(256), nullable=True),
            sa.Column("verification_token", sa.String(256), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            schema="qms",
        )

    if not _table_exists("qms_deviation_auto_trigger"):
        op.create_table(
            "qms_deviation_auto_trigger",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("trigger_type", sa.String(64), nullable=False),
            sa.Column("trigger_condition", sa.Text(), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("notify_qa", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notify_leader", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notify_reporter", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("custom_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            schema="qms",
        )

    # 索引单独建：表在历史环境中可能已存在，此时上面的 create_table 不会执行。
    op.execute("CREATE INDEX IF NOT EXISTS ix_qms_deviation_deviation_no ON qms.qms_deviation (deviation_no)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_qms_deviation_status ON qms.qms_deviation (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_qms_deviation_created_at ON qms.qms_deviation (created_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_qms_deviation_attachment_deviation_id "
        "ON qms.qms_deviation_attachment (deviation_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_qms_deviation_log_deviation_id ON qms.qms_deviation_log (deviation_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_qms_deviation_message_template_type "
        "ON qms.qms_deviation_message_template (template_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_qms_deviation_auto_trigger_type "
        "ON qms.qms_deviation_auto_trigger (trigger_type)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS qms.qms_deviation_auto_trigger")
    op.execute("DROP TABLE IF EXISTS qms.qms_deviation_feishu_bot_config")
    op.execute("DROP TABLE IF EXISTS qms.qms_deviation_message_template")
    op.execute("DROP TABLE IF EXISTS qms.qms_deviation_log")
    op.execute("DROP TABLE IF EXISTS qms.qms_deviation_attachment")
    op.execute("DROP TABLE IF EXISTS qms.qms_deviation")
