"""0123_research_template_version_kind

Revision ID: 0123_research_template_version_kind
Revises: 0122_research_report_gen_document_versions
Create Date: 2026-11-09 10:00:00.000000

给 ``research.rd_deliverable_template_versions`` 加 ``kind``，区分两类留档：

- ``template``：用户上传的 Word 母本（含回滚产生的新版本），沿用既有行为；
- ``sample``：按已保存的填充项在母本上就地写标记生成的「填充示例稿」。

示例稿要可追溯、可重复生成，但不是母本：它不置 ``is_current``、不改模板主表，
也不允许被回滚成当前版本。用一列把两种语义分开，比在版本号或文件名上打补丁可靠。

默认值 ``template``：存量记录全部是母本，回填即默认值，无需 UPDATE。
只动 research schema（单模块原则）。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0123_research_template_version_kind"
down_revision: str | Sequence[str] | None = "0122_research_report_gen_document_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_TABLE = "rd_deliverable_template_versions"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "kind",
            sa.String(length=16),
            nullable=False,
            server_default="template",
            comment="版本类型：template 母本 / sample 填充示例稿",
        ),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "kind", schema=_SCHEMA)
