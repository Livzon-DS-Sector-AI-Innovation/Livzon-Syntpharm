"""0058_add_doc_gen_core_tables

Revision ID: 0058_add_doc_gen_core_tables
Revises: 0057_merge_migration_heads
Create Date: 2026-09-09 17:40:00.000000

研发管理「文档生成」核心表（合并版）：
- doc_gen_jobs: 任务主表（含 parent_job_id/supplement_text）
- doc_gen_input_files: 输入文件
- doc_gen_slot_values: 槽位值（含 section_key/instance_index/pre_compose_text）
- doc_gen_sections: 动态章节
- doc_gen_conversations: 对话会话
- doc_gen_messages: 对话消息
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0058_add_doc_gen_core_tables'
down_revision: str | Sequence[str] | None = '0057_merge_migration_heads'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column]:
    """公共审计列（与 app/shared/base_model.py 对齐）。"""
    return [
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    ]


def _audit_fks(table: str) -> list[sa.ForeignKeyConstraint]:
    """审计列外键。"""
    return [
        sa.ForeignKeyConstraint(['created_by'], ['identity.users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id']),
    ]


def upgrade() -> None:
    # ── doc_gen_jobs（含最终字段）──
    op.create_table(
        'doc_gen_jobs',
        sa.Column('report_id', sa.Uuid(), nullable=True, comment='关联研发报告'),
        sa.Column('project_id', sa.Uuid(), nullable=True, comment='关联研发项目'),
        sa.Column('template_code', sa.String(length=100), nullable=False, comment='模板编码'),
        sa.Column('template_version', sa.String(length=20), nullable=False, comment='模板版本'),
        sa.Column('status', sa.String(length=32), nullable=False, comment='任务状态'),
        sa.Column('step', sa.String(length=64), nullable=False, comment='当前步骤说明'),
        sa.Column('progress', sa.Integer(), nullable=False, comment='进度百分比'),
        sa.Column('meta', sa.JSON(), nullable=True, comment='受控编码/版本号/品种名等元数据'),
        sa.Column('docx_object_key', sa.String(length=500), nullable=True, comment='产物 docx 存储键'),
        sa.Column('report_object_key', sa.String(length=500), nullable=True, comment='生成说明存储键'),
        sa.Column('stats', sa.JSON(), nullable=True, comment='渲染统计'),
        sa.Column('error_code', sa.String(length=64), nullable=True, comment='错误码'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误说明'),
        sa.Column('attempts', sa.Integer(), nullable=False, comment='已尝试次数'),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True, comment='租约到期'),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True, comment='完成时间'),
        sa.Column('parent_job_id', sa.Uuid(), nullable=True, comment='上一次生成任务（重新生成溯源）'),
        sa.Column('supplement_text', sa.Text(), nullable=True, comment='人工补充说明文本'),
        *_base_columns(),
        *_audit_fks('doc_gen_jobs'),
        sa.ForeignKeyConstraint(['report_id'], ['research.rd_reports.id']),
        sa.ForeignKeyConstraint(['project_id'], ['research.rd_projects.id']),
        sa.ForeignKeyConstraint(
            ['parent_job_id'], ['research.doc_gen_jobs.id'],
            name='fk_research_doc_gen_jobs_parent_job_id',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='research',
    )
    op.create_index(
        'ix_research_doc_gen_jobs_status_created', 'doc_gen_jobs', ['status', 'created_at'], schema='research'
    )

    # ── doc_gen_input_files ──
    op.create_table(
        'doc_gen_input_files',
        sa.Column('job_id', sa.Uuid(), nullable=False, comment='所属任务'),
        sa.Column('original_filename', sa.String(length=500), nullable=False, comment='原始文件名'),
        sa.Column('object_key', sa.String(length=500), nullable=False, comment='存储键或本地路径'),
        sa.Column('file_id', sa.String(length=64), nullable=False, comment='解析与引用用的稳定标识'),
        sa.Column('sha256', sa.String(length=64), nullable=False, comment='内容哈希'),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False, comment='字节数'),
        sa.Column('mime_type', sa.String(length=200), nullable=True, comment='MIME'),
        sa.Column('role', sa.String(length=32), nullable=False, comment='material/literature'),
        sa.Column('page_count', sa.Integer(), nullable=False, comment='页数估计'),
        sa.Column('char_count', sa.Integer(), nullable=False, comment='解析字符数'),
        sa.Column('parse_status', sa.String(length=32), nullable=False, comment='pending/done/failed'),
        sa.Column('warnings', sa.JSON(), nullable=True, comment='解析告警'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['job_id'], ['research.doc_gen_jobs.id']),
        *_audit_fks('doc_gen_input_files'),
        sa.PrimaryKeyConstraint('id'),
        schema='research',
    )
    op.create_index('ix_research_doc_gen_input_files_job_id', 'doc_gen_input_files', ['job_id'], schema='research')

    # ── doc_gen_slot_values（含最终字段）──
    op.create_table(
        'doc_gen_slot_values',
        sa.Column('job_id', sa.Uuid(), nullable=False, comment='所属任务'),
        sa.Column('slot_key', sa.String(length=200), nullable=False, comment='槽位 key（章节槽位带实例前缀）'),
        sa.Column('label', sa.String(length=200), nullable=False, comment='槽位名称'),
        sa.Column('text', sa.Text(), nullable=True, comment='渲染文本'),
        sa.Column('rows', sa.JSON(), nullable=True, comment='表格行数据'),
        sa.Column('state', sa.String(length=32), nullable=False, comment='结果状态'),
        sa.Column('reason', sa.Text(), nullable=True, comment='原因说明'),
        sa.Column('confidence', sa.Float(), nullable=True, comment='模型置信度'),
        sa.Column('evidence', sa.JSON(), nullable=True, comment='依据（文件/页码/原文）'),
        sa.Column('candidates', sa.JSON(), nullable=True, comment='冲突候选值'),
        sa.Column('section_key', sa.String(length=150), nullable=True, comment='所属章节实例 key'),
        sa.Column('instance_index', sa.Integer(), nullable=True, comment='章节实例序号'),
        sa.Column('pre_compose_text', sa.Text(), nullable=True, comment='成文前的人工确认文本'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['job_id'], ['research.doc_gen_jobs.id']),
        *_audit_fks('doc_gen_slot_values'),
        sa.PrimaryKeyConstraint('id'),
        schema='research',
    )
    op.create_index('ix_research_doc_gen_slot_values_job_id', 'doc_gen_slot_values', ['job_id'], schema='research')

    # ── doc_gen_sections ──
    op.create_table(
        'doc_gen_sections',
        sa.Column('job_id', sa.Uuid(), nullable=False, comment='所属任务'),
        sa.Column('section_key', sa.String(length=150), nullable=False, comment='章节实例 key'),
        sa.Column('fragment_key', sa.String(length=100), nullable=False, comment='来源章节片段 key'),
        sa.Column('extension_point_key', sa.String(length=100), nullable=False, comment='挂载的扩展点 key'),
        sa.Column('parent_section_key', sa.String(length=150), nullable=True, comment='父章节实例 key'),
        sa.Column('level', sa.Integer(), nullable=False, comment='标题层级'),
        sa.Column('title', sa.String(length=300), nullable=False, comment='章节标题'),
        sa.Column('order_index', sa.Integer(), nullable=False, comment='渲染顺序'),
        sa.Column('source', sa.String(length=16), nullable=False, comment='auto/manual'),
        sa.Column('state', sa.String(length=16), nullable=False, comment='enabled/disabled'),
        sa.Column('trigger_trace', sa.JSON(), nullable=True, comment='触发判定依据'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['job_id'], ['research.doc_gen_jobs.id']),
        *_audit_fks('doc_gen_sections'),
        sa.PrimaryKeyConstraint('id'),
        schema='research',
    )
    op.create_index(
        'ix_research_doc_gen_sections_job_order', 'doc_gen_sections', ['job_id', 'order_index'], schema='research'
    )

    # ── doc_gen_conversations ──
    op.create_table(
        'doc_gen_conversations',
        sa.Column('job_id', sa.Uuid(), nullable=False, comment='所属任务'),
        sa.Column(
            'status', sa.String(length=16), server_default='active', nullable=False, comment='active/completed/skipped'
        ),
        sa.Column('round_count', sa.Integer(), server_default='0', nullable=False, comment='已完成对话轮数'),
        sa.Column('max_rounds', sa.Integer(), server_default='3', nullable=False, comment='轮数上限'),
        sa.Column('snapshot', sa.JSON(), nullable=True, comment='创建时的槽位盘点快照'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['job_id'], ['research.doc_gen_jobs.id']),
        *_audit_fks('doc_gen_conversations'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', name='uq_research_doc_gen_conversations_job_id'),
        schema='research',
    )

    # ── doc_gen_messages ──
    op.create_table(
        'doc_gen_messages',
        sa.Column('conversation_id', sa.Uuid(), nullable=False, comment='所属会话'),
        sa.Column('role', sa.String(length=16), nullable=False, comment='user/assistant'),
        sa.Column('content', sa.Text(), nullable=False, comment='消息内容'),
        sa.Column('slot_updates', sa.JSON(), nullable=True, comment='本条消息写入的槽位变更'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['conversation_id'], ['research.doc_gen_conversations.id']),
        *_audit_fks('doc_gen_messages'),
        sa.PrimaryKeyConstraint('id'),
        schema='research',
    )
    op.create_index(
        'ix_research_doc_gen_messages_conv_created',
        'doc_gen_messages',
        ['conversation_id', 'created_at'],
        schema='research',
    )


def downgrade() -> None:
    op.drop_index('ix_research_doc_gen_messages_conv_created', table_name='doc_gen_messages', schema='research')
    op.drop_table('doc_gen_messages', schema='research')
    op.drop_table('doc_gen_conversations', schema='research')
    op.drop_index('ix_research_doc_gen_sections_job_order', table_name='doc_gen_sections', schema='research')
    op.drop_table('doc_gen_sections', schema='research')
    op.drop_index('ix_research_doc_gen_slot_values_job_id', table_name='doc_gen_slot_values', schema='research')
    op.drop_table('doc_gen_slot_values', schema='research')
    op.drop_index('ix_research_doc_gen_input_files_job_id', table_name='doc_gen_input_files', schema='research')
    op.drop_table('doc_gen_input_files', schema='research')
    op.drop_index('ix_research_doc_gen_jobs_status_created', table_name='doc_gen_jobs', schema='research')
    op.drop_table('doc_gen_jobs', schema='research')
