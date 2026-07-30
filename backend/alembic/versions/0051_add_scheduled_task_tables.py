"""0051_add_scheduled_task_tables

Revision ID: 0051_add_scheduled_task_tables
Revises: 0050_fix_work_order_order_type_check
Create Date: 2026-07-30 13:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0051_add_scheduled_task_tables'
down_revision: Union[str, None] = '0050_fix_work_order_order_type_check'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('scheduled_tasks',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False, comment='任务名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='任务描述'),
        sa.Column('cron_expression', sa.String(length=100), nullable=False, comment='Cron 表达式'),
        sa.Column('cron_desc', sa.String(length=200), nullable=True, comment='Cron 可读描述'),
        sa.Column('feishu_chat_id', sa.String(length=100), nullable=False, comment='目标飞书群聊 chat_id'),
        sa.Column('feishu_chat_name', sa.String(length=200), nullable=True, comment='飞书群聊名称'),
        sa.Column('header_color', sa.String(length=20), server_default=sa.text("'blue'"), nullable=False, comment='卡片头部颜色'),
        sa.Column('data_sources', postgresql.JSON(), nullable=True, comment='数据来源配置'),
        sa.Column('card_template', sa.Text(), nullable=True, comment='消息卡片模板'),
        sa.Column('is_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='是否启用'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True, comment='上次执行时间'),
        sa.Column('last_run_status', sa.String(length=32), nullable=True, comment='上次执行状态'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='上次错误信息'),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True, comment='下次执行时间'),
        sa.Column('created_by', postgresql.UUID(), nullable=True, comment='创建人'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['identity.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='safety'
    )
    op.create_table('scheduled_task_logs',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('task_id', postgresql.UUID(), nullable=False, comment='任务ID'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, comment='开始时间'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='完成时间'),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'running'"), nullable=False, comment='执行状态'),
        sa.Column('data_snapshot', postgresql.JSON(), nullable=True, comment='数据快照'),
        sa.Column('card_content', sa.Text(), nullable=True, comment='卡片内容'),
        sa.Column('feishu_msg_id', sa.String(length=100), nullable=True, comment='飞书消息ID'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('duration_ms', sa.Integer(), nullable=True, comment='执行耗时(毫秒)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['safety.scheduled_tasks.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='safety'
    )


def downgrade() -> None:
    op.drop_table('scheduled_task_logs', schema='safety')
    op.drop_table('scheduled_tasks', schema='safety')
