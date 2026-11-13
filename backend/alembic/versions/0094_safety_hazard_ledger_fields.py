"""safety hazard ledger fields

Revision ID: 0094_safety_hazard_ledger_fields
Revises: 0093_quality_qms_deviation_flow_tables
Create Date: 2026-11-04

隐患台账字段对齐：
1. 新增检查名称、纠正预防措施（人工）、完成/关闭日期
2. 新增三级复核审批人留痕（id / 姓名 / 时间，每级只保留最后一次）
3. status 语义收敛为关闭状态（open / closed），仅更新注释，不改类型

「证据」复用 defect_photos（整改前图片），不新增列。
只动 safety schema，单模块迁移。全部 nullable，无需回填。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0094_safety_hazard_ledger_fields"
down_revision: str = "0093_quality_qms_deviation_flow_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "hazard_reports"
_SCHEMA = "safety"

_ADD_COLUMNS: list[tuple[str, sa.types.TypeEngine]] = [
    ("inspection_name", sa.String(255)),
    ("capa_measures", sa.Text()),
    ("closed_at", sa.DateTime(timezone=True)),
    ("verify_level_1_reviewer_id", UUID(as_uuid=True)),
    ("verify_level_1_reviewer_name", sa.String(100)),
    ("verify_level_1_reviewed_at", sa.DateTime(timezone=True)),
    ("verify_level_2_reviewer_id", UUID(as_uuid=True)),
    ("verify_level_2_reviewer_name", sa.String(100)),
    ("verify_level_2_reviewed_at", sa.DateTime(timezone=True)),
    ("verify_level_3_reviewer_id", UUID(as_uuid=True)),
    ("verify_level_3_reviewer_name", sa.String(100)),
    ("verify_level_3_reviewed_at", sa.DateTime(timezone=True)),
]

_COLUMN_COMMENTS: dict[str, str] = {
    "inspection_name": "检查名称（Bitable「检查名称」）",
    "capa_measures": "纠正预防措施（人工填写，Bitable「纠正预防措施」）",
    "closed_at": "完成/关闭日期",
    "verify_level_1_reviewer_id": "一级复核审批人",
    "verify_level_1_reviewer_name": "一级复核审批人姓名",
    "verify_level_1_reviewed_at": "一级复核时间",
    "verify_level_2_reviewer_id": "二级复核审批人",
    "verify_level_2_reviewer_name": "二级复核审批人姓名",
    "verify_level_2_reviewed_at": "二级复核时间",
    "verify_level_3_reviewer_id": "三级复核审批人",
    "verify_level_3_reviewer_name": "三级复核审批人姓名",
    "verify_level_3_reviewed_at": "三级复核时间",
}

_REVIEWER_FK_COLUMNS: list[str] = [
    "verify_level_1_reviewer_id",
    "verify_level_2_reviewer_id",
    "verify_level_3_reviewer_id",
]


def upgrade() -> None:
    for name, col_type in _ADD_COLUMNS:
        op.add_column(
            _TABLE,
            sa.Column(name, col_type, nullable=True, comment=_COLUMN_COMMENTS[name]),
            schema=_SCHEMA,
        )

    for column in _REVIEWER_FK_COLUMNS:
        op.create_foreign_key(
            f"fk_{_TABLE}_{column}_identity_users",
            _TABLE,
            "users",
            [column],
            ["id"],
            source_schema=_SCHEMA,
            referent_schema="identity",
        )

    op.alter_column(
        _TABLE,
        "status",
        schema=_SCHEMA,
        existing_type=sa.String(32),
        existing_nullable=False,
        existing_server_default="open",
        comment="关闭状态: open=未关闭 / closed=已关闭",
    )


def downgrade() -> None:
    for column in _REVIEWER_FK_COLUMNS:
        op.drop_constraint(
            f"fk_{_TABLE}_{column}_identity_users",
            _TABLE,
            schema=_SCHEMA,
            type_="foreignkey",
        )

    for name, _ in reversed(_ADD_COLUMNS):
        op.drop_column(_TABLE, name, schema=_SCHEMA)

    op.alter_column(
        _TABLE,
        "status",
        schema=_SCHEMA,
        existing_type=sa.String(32),
        existing_nullable=False,
        existing_server_default="open",
        comment="状态",
    )
