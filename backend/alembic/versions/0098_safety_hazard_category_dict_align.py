"""safety hazard category dict: align comments and NOT NULL

Revision ID: 0098_safety_hazard_category_dict_align
Revises: 0097_safety_hazard_person_name_backfill
Create Date: 2026-11-09

0096 建 ``safety.hazard_categories`` 时，DDL 与 ORM 模型有三处口径不一致，
``alembic check`` 会持续报漂移（CI backend-alembic 失败）：

1. ``created_at`` / ``updated_at`` 建表时未声明 ``nullable=False``（模型继承
   ``BaseModel``，是 NOT NULL）；
2. ``hazard_categories.name``、``hazard_reports.hazard_category``、
   ``hazard_reports.rectification_responsible_person_ids`` 的列注释与模型文案不同。

0096 已在部分环境的库中执行过，改历史迁移无法回灌，所以用本条增量迁移对齐。
幂等：表不存在（0096 被跳过）时直接返回；已是 NOT NULL 的列不再重复 ALTER；
先把历史 NULL 补成 ``now()``，避免 SET NOT NULL 失败。

只动 ``safety`` schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0098_safety_hazard_category_dict_align"
down_revision: str = "0097_safety_hazard_person_name_backfill"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "safety"
_CATEGORY_TABLE = "hazard_categories"
_REPORT_TABLE = "hazard_reports"

_NAME_COMMENT = "类别名称（与 hazard_reports.hazard_category 同值）"
_REPORT_CATEGORY_COMMENT = "隐患类别：字典表 safety.hazard_categories 的 name（内置 7 类 + 用户新增）"
_LEGACY_REPORT_CATEGORY_COMMENT = "隐患类别（AI）：设备设施/危化储存/仪表+电气/…（13种）"
_RESPONSIBLE_IDS_COMMENT = (
    "整改负责人多选 UUID 列表（新）。为空时回退单人字段 rectification_responsible_person"
)
_LEGACY_RESPONSIBLE_IDS_COMMENT = "整改负责人多选 UUID 列表（新）；为空时回退单人字段"


def _column(inspector: sa.Inspector, table: str, name: str) -> dict[str, object] | None:
    return next((column for column in inspector.get_columns(table, schema=_SCHEMA) if column["name"] == name), None)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(_CATEGORY_TABLE, schema=_SCHEMA):
        return

    # 历史 NULL 先补值，SET NOT NULL 才不会因脏数据失败
    op.execute(
        sa.text(
            "UPDATE safety.hazard_categories"
            " SET created_at = COALESCE(created_at, now()), updated_at = COALESCE(updated_at, now())"
        )
    )
    for column_name in ("created_at", "updated_at"):
        column = _column(inspector, _CATEGORY_TABLE, column_name)
        if column is None or column.get("nullable") is False:
            continue
        op.alter_column(
            _CATEGORY_TABLE,
            column_name,
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            schema=_SCHEMA,
        )

    op.alter_column(
        _CATEGORY_TABLE,
        "name",
        existing_type=sa.String(64),
        existing_nullable=False,
        comment=_NAME_COMMENT,
        schema=_SCHEMA,
    )
    op.alter_column(
        _REPORT_TABLE,
        "hazard_category",
        existing_type=sa.String(64),
        existing_nullable=True,
        comment=_REPORT_CATEGORY_COMMENT,
        schema=_SCHEMA,
    )
    op.alter_column(
        _REPORT_TABLE,
        "rectification_responsible_person_ids",
        existing_type=sa.JSON(),
        existing_nullable=True,
        comment=_RESPONSIBLE_IDS_COMMENT,
        schema=_SCHEMA,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(_CATEGORY_TABLE, schema=_SCHEMA):
        return

    op.alter_column(
        _REPORT_TABLE,
        "rectification_responsible_person_ids",
        existing_type=sa.JSON(),
        existing_nullable=True,
        comment=_LEGACY_RESPONSIBLE_IDS_COMMENT,
        schema=_SCHEMA,
    )
    op.alter_column(
        _REPORT_TABLE,
        "hazard_category",
        existing_type=sa.String(64),
        existing_nullable=True,
        comment=_LEGACY_REPORT_CATEGORY_COMMENT,
        schema=_SCHEMA,
    )
    op.alter_column(
        _CATEGORY_TABLE,
        "name",
        existing_type=sa.String(64),
        existing_nullable=False,
        comment="类别名称",
        schema=_SCHEMA,
    )
    for column_name in ("created_at", "updated_at"):
        column = _column(inspector, _CATEGORY_TABLE, column_name)
        if column is None or column.get("nullable") is True:
            continue
        op.alter_column(
            _CATEGORY_TABLE,
            column_name,
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
            schema=_SCHEMA,
        )