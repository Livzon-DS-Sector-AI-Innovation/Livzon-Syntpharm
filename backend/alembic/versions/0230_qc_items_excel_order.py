"""qc_items: follow excel column order and merged headers

Revision ID: 0230_qc_items_excel_order
Revises: 0229_quality_qc_report_tables
Create Date: 2026-11-26

检验项目改为「严格照结果表 Excel 的物理列序」：

- `sort_order` 语义从「标准表序号」改为「Excel 列号（B=1 … AP=41）」
- 表头按 Excel 的合并关系跨列渲染，需要记录所属合并组与组内子列名
- 合并组内多列同名（可见异物初检占 4 列、不溶性微粒两列同名），
  唯一性必须从「项目名」改为「列位」，否则同名行插不进去

新增列：
- `standard_item_name`：标准表原始项目名，用于追溯限值来源
- `column_group_start`：所属表头组的首列列号
- `sub_label`：合并组内续列的子列名（毛 / 点 / 备注）

唯一索引：
- 删除 `uq_qc_items_product_name (product_id, item_name)`
- 新增 `uq_qc_items_product_order (product_id, sort_order)`

两者都保留「仅未软删行唯一」的部分索引形态。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0230_qc_items_excel_order"
down_revision: str | None = "0229_quality_qc_report_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "quality"
_TABLE = "qc_items"
_OLD_INDEX = "uq_qc_items_product_name"
_NEW_INDEX = "uq_qc_items_product_order"
_NOT_DELETED = sa.text("is_deleted = false")


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "standard_item_name",
            sa.String(200),
            nullable=True,
            comment="标准表原始项目名，用于追溯限值来源",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "column_group_start",
            sa.Integer(),
            nullable=True,
            comment="所属表头组的首列列号，合并表头据此跨列渲染",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "sub_label",
            sa.String(64),
            nullable=True,
            comment="合并组内续列的子列名，如 毛 / 点（总数≤5个）/ 备注",
        ),
        schema=_SCHEMA,
    )

    op.drop_index(_OLD_INDEX, table_name=_TABLE, schema=_SCHEMA)
    op.create_index(
        _NEW_INDEX,
        _TABLE,
        ["product_id", "sort_order"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=_NOT_DELETED,
    )


def downgrade() -> None:
    op.drop_index(_NEW_INDEX, table_name=_TABLE, schema=_SCHEMA, postgresql_where=_NOT_DELETED)
    op.create_index(
        _OLD_INDEX,
        _TABLE,
        ["product_id", "item_name"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=_NOT_DELETED,
    )
    op.drop_column(_TABLE, "sub_label", schema=_SCHEMA)
    op.drop_column(_TABLE, "column_group_start", schema=_SCHEMA)
    op.drop_column(_TABLE, "standard_item_name", schema=_SCHEMA)
