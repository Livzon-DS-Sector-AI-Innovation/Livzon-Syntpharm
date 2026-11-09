"""safety hazard multi responsible + progress note + category dict

Revision ID: 0096_safety_hazard_multi_responsible_and_category_dict
Revises: 0095_safety_hazard_identification_ledger_fields
Create Date: 2026-11-09

隐患登记/台账改造：
1. safety.hazard_reports 新增整改负责人多选（UUID 列表 + 姓名快照）、整改进度说明，
   并把 hazard_category 从 String(32) 放宽到 String(64)（类别可由用户新增）。
2. 新建 safety.hazard_categories 隐患类别字典表（用户新增类别全公司共享）。

历史单人字段 rectification_responsible_person(_name) 保留，读写时「多值为空则回退单值」。
只动 safety schema，单模块迁移；新增列均可空，无需回填。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0096_safety_hazard_multi_responsible_and_category_dict"
down_revision: str = "0095_safety_hazard_identification_ledger_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "hazard_reports",
        sa.Column(
            "rectification_responsible_person_ids",
            sa.JSON(),
            nullable=True,
            comment="整改负责人多选 UUID 列表（新）；为空时回退单人字段",
        ),
        schema="safety",
    )
    op.add_column(
        "hazard_reports",
        sa.Column(
            "rectification_responsible_person_names",
            sa.String(500),
            nullable=True,
            comment="整改负责人姓名快照（逗号分隔，与 ids 顺序一致）",
        ),
        schema="safety",
    )
    op.add_column(
        "hazard_reports",
        sa.Column(
            "rectification_progress_note",
            sa.Text(),
            nullable=True,
            comment="整改进度说明（自定义文字，与单选状态并存）",
        ),
        schema="safety",
    )

    # 用户新增类别可能超过 32 字符
    op.alter_column(
        "hazard_reports",
        "hazard_category",
        existing_type=sa.String(32),
        type_=sa.String(64),
        existing_nullable=True,
        schema="safety",
    )

    op.create_table(
        "hazard_categories",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, comment="类别名称"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="排序值（越小越前）"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="是否启用"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"], name="fk_hazard_categories_created_by"),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"], name="fk_hazard_categories_updated_by"),
        schema="safety",
        comment="隐患类别字典（用户可新增，全公司共享）",
    )
    op.create_index(
        "uq_hazard_categories_name",
        "hazard_categories",
        ["name"],
        unique=True,
        schema="safety",
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_hazard_categories_name", table_name="hazard_categories", schema="safety")
    op.drop_table("hazard_categories", schema="safety")

    op.alter_column(
        "hazard_reports",
        "hazard_category",
        existing_type=sa.String(64),
        type_=sa.String(32),
        existing_nullable=True,
        schema="safety",
    )
    op.drop_column("hazard_reports", "rectification_progress_note", schema="safety")
    op.drop_column("hazard_reports", "rectification_responsible_person_names", schema="safety")
    op.drop_column("hazard_reports", "rectification_responsible_person_ids", schema="safety")
