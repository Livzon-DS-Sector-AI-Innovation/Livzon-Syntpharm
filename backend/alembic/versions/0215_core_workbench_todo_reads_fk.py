"""core: 去掉 workbench_todo_reads 的跨模块 ON DELETE CASCADE

Revision ID: 0215_core_workbench_todo_reads_fk
Revises: 0207_merge_uat_and_docx_translator_heads, 0214_update_deviation_row_comments
Create Date: 2026-11-19

``0202`` 建表时把 ``user_id`` 外键写成了 ``REFERENCES identity.users(id) ON DELETE CASCADE``。
AGENTS.md 明确「允许跨模块外键，但必须避免级联删除跨模块使用」，因此改为普通外键。

``0202`` 已在 UAT 执行过（CREATE TABLE IF NOT EXISTS，重跑不会修改约束），所以这里用
幂等的 DROP + ADD 把库收敛到同一状态：新库在 ``0202`` 建表时已无 CASCADE，本迁移只是
重建同定义外键；老库借此去掉级联删除。

identity 侧用户只做软删除，孤儿已读记录由应用层清理。

挂两条父链：建表迁移 ``0202_core_workbench_todo_reads`` 在 uat 主链（经 ``0207`` 收口），
而 quality deviation 链从 ``0169`` 分叉走到 ``0214``；本迁移同时依赖两者，
保证在空库上「表已存在」再改约束（否则 ``::regclass`` 解析失败）。
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0215_core_workbench_todo_reads_fk"
down_revision: tuple[str, str] | None = (
    "0207_merge_uat_and_docx_translator_heads",
    "0214_update_deviation_row_comments",
)
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
