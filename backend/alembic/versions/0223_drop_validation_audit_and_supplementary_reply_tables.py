"""drop validation audit and supplementary reply tables

Revision ID: 0223_drop_validation_audit_and_supplementary_reply_tables
Revises: 0218_docx_translation_terms_partial_unique
Create Date: 2026-11-24

产品决定下线「验证审计」与「补充回复」两个功能，代码与入口已一并删除。

本迁移删除 6 张独立表（均属 registration schema，彼此无外键，也不被其它表引用）：

- supplementary_replies
- validation_audit_tasks
- validation_audit_files
- validation_audit_issues
- validation_audit_reports
- validation_audit_knowledge_base

已确认不保留存量数据（业务方同意直接 drop，未做数据导出）。
downgrade() 仅重建空表结构，历史数据与磁盘文件均不可恢复。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0223_drop_validation_audit_and_supplementary_reply_tables"
down_revision: str | None = "0218_docx_translation_terms_partial_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"

# 子表在前、主表在后（本功能内均为逻辑关联无外键，顺序仅为可读性）
_DROP_ORDER: tuple[str, ...] = (
    "validation_audit_files",
    "validation_audit_issues",
    "validation_audit_reports",
    "validation_audit_tasks",
    "validation_audit_knowledge_base",
    "supplementary_replies",
)


def _base_columns() -> list[sa.Column]:
    """BaseModel 公共列（与 baseline 保持一致）。"""
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
    ]


def upgrade() -> None:
    for table in _DROP_ORDER:
        op.drop_table(table, schema=_SCHEMA)


def downgrade() -> None:
    op.create_table(
        "supplementary_replies",
        sa.Column("drug_name", sa.String(length=128), nullable=False, comment="药品名称"),
        sa.Column("registration_number", sa.String(length=32), nullable=True, comment="登记号"),
        sa.Column("acceptance_number", sa.String(length=64), nullable=True, comment="受理号"),
        sa.Column("company_name", sa.String(length=256), nullable=True, comment="申请人/公司名称"),
        sa.Column("notice_file_key", sa.String(length=256), nullable=False, comment="CDE通知函文件 key"),
        sa.Column("notice_file_name", sa.String(length=256), nullable=True, comment="CDE通知函文件名"),
        sa.Column("template_file_key", sa.String(length=256), nullable=True, comment="公司模板文件 key"),
        sa.Column("template_file_name", sa.String(length=256), nullable=True, comment="公司模板文件名"),
        sa.Column("output_file_key", sa.String(length=256), nullable=False, comment="生成文件 key"),
        sa.Column("output_file_name", sa.String(length=256), nullable=False, comment="生成文件名"),
        sa.Column("question_count", sa.Integer(), server_default="0", nullable=False, comment="提取的问题数量"),
        sa.Column("remarks", sa.Text(), nullable=True, comment="备注"),
        *_base_columns(),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_supplementary_replies_drug_name", "supplementary_replies", ["drug_name"], unique=False, schema=_SCHEMA
    )
    op.create_index(
        "ix_supplementary_replies_registration_number",
        "supplementary_replies",
        ["registration_number"],
        unique=False,
        schema=_SCHEMA,
    )

    op.create_table(
        "validation_audit_tasks",
        sa.Column("task_name", sa.String(length=300), nullable=False, comment="任务名称"),
        sa.Column("product_name", sa.String(length=200), nullable=False, comment="品种名称"),
        sa.Column("method_name", sa.String(length=300), nullable=False, comment="方法名称"),
        sa.Column("source_company", sa.String(length=300), nullable=False, comment="来源公司"),
        sa.Column(
            "audit_mode", sa.String(length=30), nullable=False, comment="审核模式: protocol/report/protocol_report"
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="draft",
            nullable=False,
            comment="状态: draft/uploaded/parsing/auditing/completed/failed",
        ),
        sa.Column("conclusion", sa.String(length=30), nullable=True, comment="审核结论: pass/conditional_pass/fail"),
        sa.Column("risk_level", sa.String(length=30), nullable=True, comment="风险等级: high/medium/low"),
        sa.Column("serious_count", sa.Integer(), server_default="0", nullable=False, comment="严重问题数"),
        sa.Column("general_count", sa.Integer(), server_default="0", nullable=False, comment="一般问题数"),
        sa.Column("suggestion_count", sa.Integer(), server_default="0", nullable=False, comment="建议优化数"),
        sa.Column("compliant_count", sa.Integer(), server_default="0", nullable=False, comment="合规项数"),
        sa.Column("non_compliant_count", sa.Integer(), server_default="0", nullable=False, comment="不合规项数"),
        sa.Column("report_path", sa.String(length=500), nullable=True, comment="审核报告文件路径"),
        *_base_columns(),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_validation_audit_tasks_source_company",
        "validation_audit_tasks",
        ["source_company"],
        unique=False,
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_validation_audit_tasks_status", "validation_audit_tasks", ["status"], unique=False, schema=_SCHEMA
    )

    op.create_table(
        "validation_audit_files",
        sa.Column("task_id", sa.UUID(), nullable=False, comment="任务ID（逻辑关联）"),
        sa.Column(
            "file_type", sa.String(length=30), nullable=False, comment="文件类型: protocol/report/attachment"
        ),
        sa.Column("original_filename", sa.String(length=500), nullable=False, comment="原始文件名"),
        sa.Column("file_path", sa.String(length=500), nullable=False, comment="文件存储路径"),
        sa.Column("file_size", sa.Integer(), server_default="0", nullable=False, comment="文件大小(字节)"),
        sa.Column(
            "parse_status",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
            comment="解析状态: pending/parsing/completed/failed",
        ),
        sa.Column("parsed_text", sa.Text(), nullable=True, comment="解析后的文本内容"),
        *_base_columns(),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_validation_audit_files_task_id", "validation_audit_files", ["task_id"], unique=False, schema=_SCHEMA
    )

    op.create_table(
        "validation_audit_issues",
        sa.Column("task_id", sa.UUID(), nullable=False, comment="任务ID（逻辑关联）"),
        sa.Column("file_id", sa.UUID(), nullable=True, comment="文件ID（逻辑关联）"),
        sa.Column("issue_no", sa.String(length=20), nullable=False, comment="问题编号，如 P001"),
        sa.Column("dimension", sa.String(length=100), nullable=False, comment="所属维度"),
        sa.Column("check_item", sa.String(length=200), nullable=False, comment="检查项"),
        sa.Column("description", sa.Text(), nullable=False, comment="问题描述"),
        sa.Column("suggestion", sa.Text(), nullable=True, comment="修改建议"),
        sa.Column("issue_type", sa.String(length=20), nullable=False, comment="问题类型: serious/general/suggestion"),
        sa.Column("page_no", sa.Integer(), nullable=True, comment="所在页码"),
        sa.Column("evidence_text", sa.Text(), nullable=True, comment="证据原文"),
        *_base_columns(),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_validation_audit_issues_file_id", "validation_audit_issues", ["file_id"], unique=False, schema=_SCHEMA
    )
    op.create_index(
        "ix_validation_audit_issues_task_id", "validation_audit_issues", ["task_id"], unique=False, schema=_SCHEMA
    )

    op.create_table(
        "validation_audit_reports",
        sa.Column("task_id", sa.UUID(), nullable=False, comment="任务ID（逻辑关联）"),
        sa.Column("report_title", sa.String(length=500), nullable=False, comment="报告标题"),
        sa.Column("report_markdown", sa.Text(), nullable=True, comment="报告 Markdown 内容"),
        sa.Column("report_file_path", sa.String(length=500), nullable=True, comment="报告文件路径"),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False, comment="报告版本"),
        *_base_columns(),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_validation_audit_reports_task_id", "validation_audit_reports", ["task_id"], unique=False, schema=_SCHEMA
    )

    op.create_table(
        "validation_audit_knowledge_base",
        sa.Column("dimension", sa.String(length=100), nullable=False, comment="所属维度"),
        sa.Column("check_item", sa.String(length=200), nullable=False, comment="检查项"),
        sa.Column("issue_type", sa.String(length=20), nullable=False, comment="问题类型: serious/general/suggestion"),
        sa.Column("description_template", sa.Text(), nullable=True, comment="问题描述模板"),
        sa.Column("suggestion_template", sa.Text(), nullable=True, comment="修改建议模板"),
        sa.Column("frequency", sa.Integer(), server_default="1", nullable=False, comment="出现频次"),
        sa.Column("related_product", sa.String(length=200), nullable=True, comment="涉及品种"),
        sa.Column("source_task_id", sa.UUID(), nullable=True, comment="来源任务ID（逻辑关联）"),
        *_base_columns(),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_validation_audit_kb_source_task_id",
        "validation_audit_knowledge_base",
        ["source_task_id"],
        unique=False,
        schema=_SCHEMA,
    )
