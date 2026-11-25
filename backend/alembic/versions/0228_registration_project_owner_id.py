"""add owner_id to registration projects

Revision ID: 0228_registration_project_owner_id
Revises: 0227_merge_uat_permission_and_review_heads
Create Date: 2026-11-25

注册项目「负责人」改为存用户 UUID（人员选择统一存 UUID 的规范），
保留 owner 姓名快照列用于免联表展示与历史数据兼容：

- owner_id：可空 UUID，外键指向 identity.users.id（与 created_by/updated_by 一致）
- owner：语义收窄为「姓名快照」，历史行不回填、继续可读

历史数据仅回填 owner_id 为空的行会被跳过（无 ID 可推），不做数据猜测。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0228_registration_project_owner_id"
down_revision: str | None = "0227_merge_uat_permission_and_review_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"
_TABLE = "registration_projects"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "owner_id",
            sa.Uuid(),
            nullable=True,
            comment="负责人用户 ID（人员选择存 UUID）",
        ),
        schema=_SCHEMA,
    )
    op.create_foreign_key(
        "fk_registration_projects_owner_id_users",
        _TABLE,
        "users",
        ["owner_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema="identity",
    )
    op.alter_column(
        _TABLE,
        "owner",
        existing_type=sa.String(length=128),
        existing_nullable=True,
        comment="负责人姓名快照",
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint("fk_registration_projects_owner_id_users", _TABLE, schema=_SCHEMA, type_="foreignkey")
    op.drop_column(_TABLE, "owner_id", schema=_SCHEMA)
