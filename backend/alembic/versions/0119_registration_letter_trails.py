"""registration authorization letter trails

Revision ID: 0119_registration_letter_trails
Revises: 0118_registration_project_stage_logs
Create Date: 2026-11-12

授权书管理页改版：新建 authorization_letter_trails 留痕日志表（审计追踪，只增不删），
记录授权书的生成/下载动作、操作人与模板版本；
并按现有授权书记录补录 generate 留痕（操作人取记录的 created_by，可能为空）。

只动 registration schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0119_registration_letter_trails"
down_revision: str = "0118_registration_project_stage_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"


def upgrade() -> None:
    op.create_table(
        "authorization_letter_trails",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "letter_id",
            UUID(as_uuid=True),
            sa.ForeignKey("registration.authorization_letters.id"),
            nullable=False,
            comment="授权书记录ID",
        ),
        sa.Column("action", sa.String(16), nullable=False, comment="动作：generate=生成 / download=下载"),
        sa.Column("detail", sa.Text(), nullable=False, comment="留痕描述（生成时记模板版本）"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema=_SCHEMA,
    )
    op.create_check_constraint(
        "ck_authorization_letter_trails_action",
        "authorization_letter_trails",
        "action IN ('generate', 'download')",
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_authorization_letter_trails_letter", "authorization_letter_trails", ["letter_id"], schema=_SCHEMA
    )

    # 存量授权书补录「生成」留痕：时间与操作人取自原记录
    op.execute(
        f"""
        INSERT INTO {_SCHEMA}.authorization_letter_trails
            (id, letter_id, action, detail, created_at, updated_at, created_by, is_deleted)
        SELECT gen_random_uuid(), l.id, 'generate', '生成授权书（历史记录补录）',
               l.created_at, l.created_at, l.created_by, false
        FROM {_SCHEMA}.authorization_letters l
        WHERE l.is_deleted = false
        """
    )


def downgrade() -> None:
    op.drop_index("ix_authorization_letter_trails_letter", table_name="authorization_letter_trails", schema=_SCHEMA)
    op.drop_constraint(
        "ck_authorization_letter_trails_action", "authorization_letter_trails", type_="check", schema=_SCHEMA
    )
    op.drop_table("authorization_letter_trails", schema=_SCHEMA)
