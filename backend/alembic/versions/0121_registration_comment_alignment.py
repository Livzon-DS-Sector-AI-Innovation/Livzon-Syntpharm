"""align registration column comments

Revision ID: 0121_registration_comment_alignment
Revises: 0120_merge_main_and_registration_heads
Create Date: 2026-11-13

同步注册模块模型与数据库中的列注释，不涉及类型或约束变更。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0121_registration_comment_alignment"
down_revision: str = "0120_merge_main_and_registration_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"


def upgrade() -> None:
    op.alter_column(
        "drug_nodes",
        "skipped",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("false"),
        comment="是否跳过（节点不发生，如核查豁免/无发补），与 actual_date 互斥",
        schema=_SCHEMA,
    )
    op.alter_column(
        "registration_projects",
        "registration_type",
        existing_type=sa.String(length=64),
        existing_nullable=True,
        comment="注册类型（新注册/再注册/变更/补充申请）",
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.alter_column(
        "drug_nodes",
        "skipped",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("false"),
        comment="是否跳过（节点不发生，如核查豁免/无发补）",
        schema=_SCHEMA,
    )
    op.alter_column(
        "registration_projects",
        "registration_type",
        existing_type=sa.String(length=64),
        existing_nullable=True,
        comment="注册类型（新注册/再注册/变更等）",
        schema=_SCHEMA,
    )
