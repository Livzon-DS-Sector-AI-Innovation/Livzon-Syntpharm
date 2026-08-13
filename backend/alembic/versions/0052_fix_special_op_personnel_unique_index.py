"""0052_fix_special_op_personnel_unique_index

Revision ID: 0052_fix_special_op_personnel_unique_index
Revises: 0051_add_scheduled_task_tables
Create Date: 2026-08-13 16:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0052_fix_special_op_personnel_unique_index'
down_revision: Union[str, None] = '0051_add_scheduled_task_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # 删除旧的人员编号唯一索引（如果存在）
    result = conn.execute(sa.text("SELECT indexname FROM pg_indexes WHERE schemaname='safety' AND indexname='uq_special_op_personnel_no'"))
    if result.fetchone():
        op.drop_index(
            'uq_special_op_personnel_no',
            table_name='special_operation_personnel',
            schema='safety',
        )
    # 检查新索引是否已存在
    result = conn.execute(sa.text("SELECT indexname FROM pg_indexes WHERE schemaname='safety' AND indexname='uq_special_op_personnel_duplicate'"))
    if not result.fetchone():
        # 创建新的复合唯一索引（人员编号 + 部门 + 证书类型 + 证书编号 + 到期日期）
        op.create_index(
            'uq_special_op_personnel_duplicate',
            'special_operation_personnel',
            ['personnel_no', 'department', 'certificate_type', 'certificate_number', 'expiry_date'],
            unique=True,
            schema='safety',
            postgresql_where=sa.text('is_deleted = false'),
        )


def downgrade() -> None:
    # 删除新的复合唯一索引
    op.drop_index(
        'uq_special_op_personnel_duplicate',
        table_name='special_operation_personnel',
        schema='safety',
    )
    # 恢复旧的人员编号唯一索引
    op.create_index(
        'uq_special_op_personnel_no',
        'special_operation_personnel',
        ['personnel_no'],
        unique=True,
        schema='safety',
        postgresql_where=sa.text('is_deleted = false'),
    )
