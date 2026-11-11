"""add department contact qa reviewer fields

Revision ID: 0105_add_department_contact_qa_reviewer_fields
Revises: 0104_deprecate_deviation_settings_permissions
Create Date: 2026-11-11

部门联系人把「QA 人员」文本数组按位置约定（[0]=所属QA、[1]=QA负责人）拆成两个
独立的用户外键列，让「所属QA审核」与「QA负责人审核」两个流程节点直接对应配置字段，
不再依赖数组顺序：

- ``qa_reviewer_id``：所属 QA
- ``qa_head_id``：QA 负责人

回填只处理历史值本身是平台用户 UUID 且用户仍存在的行；飞书 open_id 形态无法映射到
用户主键，保持 NULL，由 ``deviation_flow.resolve_step_handlers`` 的旧数组回退链兜底。
``qa_staff_ids`` 保留不删（导入与种子脚本仍写该列），保存时由服务层同步写入。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0105_add_department_contact_qa_reviewer_fields"
down_revision: str = "0104_deprecate_deviation_settings_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "quality"
_TABLE = "department_contacts"

#: 历史数组里只有这种形态才能安全转成用户主键，open_id 形态留给运行期回退
_UUID_PATTERN = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

_BACKFILL_QA_REVIEWER = sa.text(
    "UPDATE quality.department_contacts AS c "
    "SET qa_reviewer_id = c.qa_staff_ids[1]::uuid "
    "WHERE c.qa_reviewer_id IS NULL "
    "  AND coalesce(array_length(c.qa_staff_ids, 1), 0) >= 1 "
    "  AND c.qa_staff_ids[1] ~* :pattern "
    "  AND EXISTS (SELECT 1 FROM identity.users u WHERE u.id = c.qa_staff_ids[1]::uuid)"
)

_BACKFILL_QA_HEAD = sa.text(
    "UPDATE quality.department_contacts AS c "
    "SET qa_head_id = c.qa_staff_ids[2]::uuid "
    "WHERE c.qa_head_id IS NULL "
    "  AND coalesce(array_length(c.qa_staff_ids, 1), 0) >= 2 "
    "  AND c.qa_staff_ids[2] ~* :pattern "
    "  AND EXISTS (SELECT 1 FROM identity.users u WHERE u.id = c.qa_staff_ids[2]::uuid)"
)


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "qa_reviewer_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="所属 QA",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "qa_head_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="QA 负责人",
        ),
        schema=_SCHEMA,
    )

    bind = op.get_bind()
    bind.execute(_BACKFILL_QA_REVIEWER, {"pattern": _UUID_PATTERN})
    bind.execute(_BACKFILL_QA_HEAD, {"pattern": _UUID_PATTERN})


def downgrade() -> None:
    """只回退列；数据已由 qa_staff_ids 保留，无需回滚。"""
    op.drop_column(_TABLE, "qa_head_id", schema=_SCHEMA)
    op.drop_column(_TABLE, "qa_reviewer_id", schema=_SCHEMA)
