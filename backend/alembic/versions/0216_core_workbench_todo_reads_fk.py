"""core: 去掉 workbench_todo_reads 的跨模块 ON DELETE CASCADE

Revision ID: 0216_core_workbench_todo_reads_fk
Revises: 0215_core_workbench_todo_reads
Create Date: 2026-11-19

``0133`` 建表时把 ``user_id`` 外键写成了 ``REFERENCES identity.users(id) ON DELETE CASCADE``。
AGENTS.md 明确「允许跨模块外键，但必须避免级联删除跨模块使用」，因此改为普通外键。

``0133`` 已在 UAT 执行过（CREATE TABLE IF NOT EXISTS，重跑不会修改约束），所以这里用
幂等的 DROP + ADD 把库收敛到同一状态：新库在 ``0133`` 建表时已无 CASCADE，本迁移只是
重建同定义外键；老库借此去掉级联删除。

identity 侧用户只做软删除，孤儿已读记录由应用层清理。
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0216_core_workbench_todo_reads_fk"
down_revision: str | None = "0215_core_workbench_todo_reads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "core"
_TABLE = "workbench_todo_reads"
_FK = "workbench_todo_reads_user_id_fkey"


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{_FK}' AND conrelid = '{_SCHEMA}.{_TABLE}'::regclass
            ) THEN
                ALTER TABLE {_SCHEMA}.{_TABLE} DROP CONSTRAINT {_FK};
            END IF;
            ALTER TABLE {_SCHEMA}.{_TABLE}
                ADD CONSTRAINT {_FK} FOREIGN KEY (user_id) REFERENCES identity.users(id);
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE {_SCHEMA}.{_TABLE} DROP CONSTRAINT IF EXISTS {_FK}")
    op.execute(
        f"""
        ALTER TABLE {_SCHEMA}.{_TABLE}
            ADD CONSTRAINT {_FK} FOREIGN KEY (user_id)
            REFERENCES identity.users(id) ON DELETE CASCADE
        """
    )
