"""0078_add_doc_gen_job_env

Revision ID: 0078_add_doc_gen_job_env
Revises: 0077_drop_template_markdown_ai
Create Date: 2026-09-30 13:00:00.000000

文档生成任务增加环境标签列 ``env``：多套部署（本地/UAT）共用同一库时，
worker 只领取 ``env`` 等于本部署 ``DOC_GEN_WORKER_ENV``（缺省回退 ``APP_ENV``）
的任务，启动恢复也只收口本环境中断任务，避免跨环境抢任务、误杀对方执行中的任务。

存量行取 ``'default'``：不会被带标签的 worker 领取，属预期（历史任务均已终态；
若升级时存在排队中的旧任务，需人工重试或改标签后由对应环境领取）。
幂等新增（列/索引已存在即跳过）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0078_add_doc_gen_job_env"
down_revision: str | Sequence[str] | None = "0077_drop_template_markdown_ai"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "doc_gen_jobs"
_SCHEMA = "research"
_INDEX = "ix_research_doc_gen_jobs_env_status_created"


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(_TABLE, schema=_SCHEMA)]

    if "env" not in columns:
        op.add_column(
            _TABLE,
            sa.Column(
                "env",
                sa.String(length=32),
                nullable=False,
                server_default="default",
                comment="任务环境标签",
            ),
            schema=_SCHEMA,
        )
    indexes = [idx["name"] for idx in inspector.get_indexes(_TABLE, schema=_SCHEMA)]
    if _INDEX not in indexes:
        op.create_index(_INDEX, _TABLE, ["env", "status", "created_at"], schema=_SCHEMA)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = [idx["name"] for idx in inspector.get_indexes(_TABLE, schema=_SCHEMA)]
    if _INDEX in indexes:
        op.drop_index(_INDEX, table_name=_TABLE, schema=_SCHEMA)
    columns = [col["name"] for col in inspector.get_columns(_TABLE, schema=_SCHEMA)]
    if "env" in columns:
        op.drop_column(_TABLE, "env", schema=_SCHEMA)
