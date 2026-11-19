"""core: workbench_todo_reads（顶栏待办已读登记）

Revision ID: 0133_core_workbench_todo_reads
Revises: 0132_core_module_setting_metadata
Create Date: 2026-11-18

顶栏「消息提醒」原来只有待办总数，没有已读概念。本次新增按用户登记的已读表：

- 唯一键 ``(user_id, source, item_id)``：一条待办只保留一条已读记录，重复标记走 upsert；
- ``fingerprint``：标记时的内容指纹（状态 + 当前环节 + 判定依据）。单据推进后指纹变化，
  旧记录不再命中，自动重新计入未读，避免「标了已读就再没人管」；
- ``user_id`` 外键：普通外键，不做 ON DELETE CASCADE（跨模块禁止级联删除，用户行
  只做软删除，孤儿已读记录由 ``0134`` 与应用层负责清理）。

表放 ``core`` schema（平台基础设施），只涉及单一 schema。建表用 IF NOT EXISTS 语义，
重复执行不失败（本仓库存在历史分叉库，容错优先）。
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0133_core_workbench_todo_reads"
down_revision: str | None = "0132_core_module_setting_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "core"
_TABLE = "workbench_todo_reads"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_SCHEMA}.{_TABLE} (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES identity.users(id),
            source VARCHAR(100) NOT NULL,
            item_id VARCHAR(64) NOT NULL,
            fingerprint VARCHAR(255) NOT NULL,
            read_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID REFERENCES identity.users(id),
            updated_by UUID REFERENCES identity.users(id),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            CONSTRAINT uq_workbench_todo_reads_user_item UNIQUE (user_id, source, item_id)
        )
        """
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_workbench_todo_reads_user_id ON {_SCHEMA}.{_TABLE} (user_id)"
    )
    op.execute(
        f"COMMENT ON TABLE {_SCHEMA}.{_TABLE} IS '顶栏待办已读登记（用户 + 数据源 + 单据 + 内容指纹）'"
    )
    op.execute(f"COMMENT ON COLUMN {_SCHEMA}.{_TABLE}.user_id IS '已读用户'")
    op.execute(f"COMMENT ON COLUMN {_SCHEMA}.{_TABLE}.source IS '数据源标识，如 quality.deviation.todos'")
    op.execute(f"COMMENT ON COLUMN {_SCHEMA}.{_TABLE}.item_id IS '待办条目 ID'")
    op.execute(f"COMMENT ON COLUMN {_SCHEMA}.{_TABLE}.fingerprint IS '内容指纹：状态|当前环节|判定依据'")
    op.execute(f"COMMENT ON COLUMN {_SCHEMA}.{_TABLE}.read_at IS '最近一次标记已读时间'")


def downgrade() -> None:
    op.execute(f"DROP TABLE IF EXISTS {_SCHEMA}.{_TABLE}")
