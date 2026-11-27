"""qc_items: record where the three-layer standards came from

Revision ID: 0231_qc_items_standard_source
Revises: 0230_qc_items_excel_order
Create Date: 2026-11-26

导入时把「标准表 docx」与「结果表 Excel 第 3/4/5 行」逐列比对：
一致即通过，不一致由人逐条选择，只有一边有时按有值方采用。

为了以后能回答「这一列的标准当时是从哪份文件来的、是不是人工选过」，
在 `qc_items` 上记录来源：

- `excel`：取自结果表该列
- `docx`：取自标准表（结果表该层为空）
- `none`：人工选择「这层留空」
- `mixed`：同一列不同层来源不同
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0231_qc_items_standard_source"
down_revision: str | None = "0230_qc_items_excel_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "quality"
_TABLE = "qc_items"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "standard_source",
            sa.String(16),
            nullable=True,
            comment="本列三层标准取自哪份文件：excel 结果表 / docx 标准表 / none 人工留空 / mixed 各层不同",
        ),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "standard_source", schema=_SCHEMA)
