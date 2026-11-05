"""safety hazard identification ledger fields

Revision ID: 0111_safety_hazard_identification_ledger_fields
Revises: 0110_safety_hazard_ledger_fields
Create Date: 2026-11-05

危险源辨识台账字段扩展：
承载历史《危险源辨识管控清单》导入所需的原始字段（风险点、作业单元、检查标准等 12 列）。

全部 nullable，无需回填；只动 safety schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0111_safety_hazard_identification_ledger_fields"
down_revision: str = "0110_safety_hazard_ledger_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "hazard_identifications"
_SCHEMA = "safety"

_ADD_COLUMNS: list[tuple[str, sa.types.TypeEngine]] = [
    ("checklist_no", sa.String(64)),
    ("risk_point_no", sa.String(255)),
    ("risk_point_type", sa.String(64)),
    ("risk_point_name", sa.String(255)),
    ("work_unit", sa.String(255)),
    ("location_tag", sa.String(500)),
    ("work_step", sa.Text()),
    ("check_standard", sa.Text()),
    ("risk_method", sa.String(10)),
    ("severity_s", sa.Float()),
    ("control_unit", sa.String(100)),
    ("training_measures", sa.Text()),
]

_COLUMN_COMMENTS: dict[str, str] = {
    "checklist_no": "检查表编号",
    "risk_point_no": "风险点编号",
    "risk_point_type": "风险点类型",
    "risk_point_name": "风险点名称",
    "work_unit": "作业单元/区域",
    "location_tag": "位号/部位",
    "work_step": "作业步骤/检查项目",
    "check_standard": "检查标准",
    "risk_method": "风险评价方法（LEC/LS）",
    "severity_s": "严重性S（LS法）",
    "control_unit": "管控单位",
    "training_measures": "现有培训教育措施",
}


def upgrade() -> None:
    # 本地共享库可能已被其他分支的 DDL 补过列，这里按实际列名跳过，保证可重复执行
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(_TABLE, schema=_SCHEMA)}
    for name, col_type in _ADD_COLUMNS:
        if name in existing:
            continue
        op.add_column(
            _TABLE,
            sa.Column(name, col_type, nullable=True, comment=_COLUMN_COMMENTS[name]),
            schema=_SCHEMA,
        )


def downgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(_TABLE, schema=_SCHEMA)}
    for name, _ in reversed(_ADD_COLUMNS):
        if name not in existing:
            continue
        op.drop_column(_TABLE, name, schema=_SCHEMA)
