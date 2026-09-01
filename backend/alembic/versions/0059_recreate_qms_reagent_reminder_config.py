"""0056_recreate_qms_reagent_reminder_config

Revision ID: 0056_recreate_qms_reagent_reminder_config
Revises: d89b9d01b93a
Create Date: 2026-08-27

0033_fix_remaining_model_changes 的 upgrade() 删除了 qms.qms_reagent_reminder_config 表，
且无后续迁移重建，导致全新数据库（e2e/新部署）迁移到 head 后该表缺失，
GET /api/v1/quality/reagent-reminder/config 返回 500。
本迁移按当前模型定义（app/modules/quality/qms/reagent_reminder_config.py）重建该表。
CREATE SCHEMA/TABLE IF NOT EXISTS：防御个别环境 schema 缺失或表仍存在的异常。
经总负责人批准；alembic/ 属架构负责人辖区，已在 PR #41 披露。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0059_recreate_qms_reagent_reminder_config"
down_revision: str | None = "0058_merge_migration_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS qms"))
    op.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS qms.qms_reagent_reminder_config (
            id UUID NOT NULL,
            feishu_app_id VARCHAR(128),
            feishu_app_secret VARCHAR(256),
            feishu_chat_id VARCHAR(128),
            low_stock_threshold INTEGER NOT NULL,
            is_enabled BOOLEAN NOT NULL,
            last_remind_time TIMESTAMP,
            last_remind_content TEXT,
            created_by UUID,
            created_at TIMESTAMP NOT NULL,
            updated_by UUID,
            updated_at TIMESTAMP,
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            CONSTRAINT qms_reagent_reminder_config_pkey PRIMARY KEY (id)
        )
    """)
    )
    comments = {
        "feishu_app_id": "飞书应用 AppID",
        "feishu_app_secret": "飞书应用 AppSecret",
        "feishu_chat_id": "飞书群 ID",
        "low_stock_threshold": "库存不足阈值（默认2）",
        "is_enabled": "是否启用提醒",
        "last_remind_time": "上次提醒时间",
        "last_remind_content": "上次提醒内容",
        "created_by": "创建人",
        "created_at": "创建时间",
        "updated_by": "更新人",
        "updated_at": "更新时间",
        "is_deleted": "是否删除",
    }
    op.execute(sa.text("COMMENT ON TABLE qms.qms_reagent_reminder_config IS '试剂提醒配置表'"))
    for col, comment in comments.items():
        op.execute(sa.text(f"COMMENT ON COLUMN qms.qms_reagent_reminder_config.{col} IS '{comment}'"))


def downgrade() -> None:
    op.drop_table("qms_reagent_reminder_config", schema="qms")
