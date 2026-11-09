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

本地共享开发库可能已被其他分支的 DDL 补过同一批列/表，这里按实际结构跳过，
保证可重复执行（与 0095 相同的幂等策略）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0096_safety_hazard_multi_responsible_and_category_dict"
down_revision: str = "0095_safety_hazard_identification_ledger_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "hazard_reports"
_SCHEMA = "safety"

_ADD_COLUMNS: list[tuple[str, sa.types.TypeEngine, str]] = [
    (
        "rectification_responsible_person_ids",
        sa.JSON(),
        "整改负责人多选 UUID 列表（新）；为空时回退单人字段",
    ),
    (
        "rectification_responsible_person_names",
        sa.String(500),
        "整改负责人姓名快照（逗号分隔，与 ids 顺序一致）",
    ),
    (
        "rectification_progress_note",
        sa.Text(),
        "整改进度说明（自定义文字，与单选状态并存）",
    ),
]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    existing_columns = {column["name"] for column in inspector.get_columns(_TABLE, schema=_SCHEMA)}
    for name, col_type, comment in _ADD_COLUMNS:
        if name in existing_columns:
            continue
        op.add_column(
            _TABLE,
            sa.Column(name, col_type, nullable=True, comment=comment),
            schema=_SCHEMA,
        )

    # 用户新增类别可能超过 32 字符；已是 64 时跳过，避免无意义的重写表
    category_column = next(
        (column for column in inspector.get_columns(_TABLE, schema=_SCHEMA) if column["name"] == "hazard_category"),
        None,
    )
    current_length = getattr(category_column["type"], "length", None) if category_column else None
    if current_length != 64:
        op.alter_column(
            _TABLE,
            "hazard_category",
            existing_type=sa.String(current_length or 32),
            type_=sa.String(64),
            existing_nullable=True,
            schema=_SCHEMA,
        )

    if not inspector.has_table("hazard_categories", schema=_SCHEMA):
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
            sa.ForeignKeyConstraint(
                ["created_by"], ["identity.users.id"], name="fk_hazard_categories_created_by"
            ),
            sa.ForeignKeyConstraint(
                ["updated_by"], ["identity.users.id"], name="fk_hazard_categories_updated_by"
            ),
            schema=_SCHEMA,
            comment="隐患类别字典（用户可新增，全公司共享）",
        )

    existing_indexes = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("hazard_categories", schema=_SCHEMA)
    }
    if "uq_hazard_categories_name" not in existing_indexes:
        op.create_index(
            "uq_hazard_categories_name",
            "hazard_categories",
            ["name"],
            unique=True,
            schema=_SCHEMA,
            postgresql_where=sa.text("is_deleted = false"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if inspector.has_table("hazard_categories", schema=_SCHEMA):
        indexes = {index["name"] for index in inspector.get_indexes("hazard_categories", schema=_SCHEMA)}
        if "uq_hazard_categories_name" in indexes:
            op.drop_index("uq_hazard_categories_name", table_name="hazard_categories", schema=_SCHEMA)
        op.drop_table("hazard_categories", schema=_SCHEMA)

    existing_columns = {column["name"] for column in inspector.get_columns(_TABLE, schema=_SCHEMA)}
    category_column = next(
        (column for column in inspector.get_columns(_TABLE, schema=_SCHEMA) if column["name"] == "hazard_category"),
        None,
    )
    current_length = getattr(category_column["type"], "length", None) if category_column else None
    if current_length == 64:
        op.alter_column(
            _TABLE,
            "hazard_category",
            existing_type=sa.String(64),
            type_=sa.String(32),
            existing_nullable=True,
            schema=_SCHEMA,
        )

    for name, _, _ in reversed(_ADD_COLUMNS):
        if name not in existing_columns:
            continue
        op.drop_column(_TABLE, name, schema=_SCHEMA)