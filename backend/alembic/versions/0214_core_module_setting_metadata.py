"""core: module_settings 增加展示元数据（中文名 / 功能域 / 密钥类 / 取值提示）

Revision ID: 0214_core_module_setting_metadata
Revises: 0213_permission_role_sync_lock
Create Date: 2026-11-18

模块配置页要从「英文 key 表格」升级成「可检索、可分组、可就地编辑的配置清单」，
需要配置项自带展示元数据：

- ``label``：中文名，界面主标题；未回填时前端回退显示 key
- ``group_name``：功能域分组（如「AI 模型」「飞书集成」），未回填归入「其他」
- ``is_secret``：密钥类配置，列表只返回掩码、导出不含明文
- ``value_hint``：取值提示 / 取值范围，编辑时展示

四列全部可空或带默认值，纯追加，不影响存量数据；元数据由
``scripts/seed/seed_module_settings.py`` 的幂等回填补齐。

列用 IF NOT EXISTS 语义写入，重复执行不会失败（本仓库存在历史分叉库，容错优先）。

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0214_core_module_setting_metadata"
down_revision: str | None = "0213_permission_role_sync_lock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "core"
_TABLE = "module_settings"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {_SCHEMA}.{_TABLE} ADD COLUMN IF NOT EXISTS label VARCHAR(100)")
    op.execute(f"ALTER TABLE {_SCHEMA}.{_TABLE} ADD COLUMN IF NOT EXISTS group_name VARCHAR(50)")
    op.execute(
        f"ALTER TABLE {_SCHEMA}.{_TABLE} ADD COLUMN IF NOT EXISTS is_secret BOOLEAN NOT NULL DEFAULT false"
    )
    op.execute(f"ALTER TABLE {_SCHEMA}.{_TABLE} ADD COLUMN IF NOT EXISTS value_hint VARCHAR(200)")

    op.execute(
        f"COMMENT ON COLUMN {_SCHEMA}.{_TABLE}.label IS '配置项中文名（未回填时界面回退显示 key）'"
    )
    op.execute(
        f"COMMENT ON COLUMN {_SCHEMA}.{_TABLE}.group_name IS '功能域分组名（未回填时归入「其他」）'"
    )
    op.execute(
        f"COMMENT ON COLUMN {_SCHEMA}.{_TABLE}.is_secret IS '是否密钥类配置（列表只返回掩码，导出不含明文）'"
    )
    op.execute(
        f"COMMENT ON COLUMN {_SCHEMA}.{_TABLE}.value_hint IS '取值提示 / 取值范围（界面在编辑框中提示）'"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE {_SCHEMA}.{_TABLE} DROP COLUMN IF EXISTS value_hint")
    op.execute(f"ALTER TABLE {_SCHEMA}.{_TABLE} DROP COLUMN IF EXISTS is_secret")
    op.execute(f"ALTER TABLE {_SCHEMA}.{_TABLE} DROP COLUMN IF EXISTS group_name")
    op.execute(f"ALTER TABLE {_SCHEMA}.{_TABLE} DROP COLUMN IF EXISTS label")
