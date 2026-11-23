"""permission: 退役历史内置角色（负责人 head / 管理员 manager）

Revision ID: 0220_permission_role_owner_delegate
Revises: 0216_core_workbench_todo_reads_fk
Create Date: 2026-11-19

背景（TC-009 + 2026-11-19 需求）：
- 旧内置角色是 ``{module}:head``（XX负责人）/ ``{module}:manager``（XX管理员）；
- 新产品口径只保留 ``{module}:owner``（模块负责人）/ ``{module}:delegate``（模块代表），
  其中「模块代表」由模块负责人在模块配置页指派；
- 用户决策：旧角色**直接退役**（角色与其授权一起停用），不把授权迁移到新角色。

本迁移只改数据状态，不新增/改名角色：owner/delegate 由应用启动时的
``_sync_roles`` 按注册表幂等创建。

形态兼容与幂等：
- 干净环境（只有 head/manager）：命中并停用；owner/delegate 启动后创建；
- 新旧并存环境：只停 head/manager，不触碰已有 owner/delegate（不再有唯一约束冲突）；
- 曾执行过初版（改名版）0203 的环境：revision 已记录，Alembic 不会重跑，
  本脚本在其上命中 0 行、不报错。注意该环境下 ``downgrade`` 语义也由
  「改回 head/manager」变为 no-op —— code 已被永久改写，本脚本无法还原。

部署门禁（执行前人工只读检查）：
1. ``SELECT version_num FROM public.alembic_version``；
   若已含 ``0220_permission_role_owner_delegate``，说明该环境执行过改名版，
   head/manager 的授权已挂在 owner 名下，需按清单人工核对后再发布。
2. 发布说明需附「旧角色活跃授权清单」，迁移后由系统管理员重新指派 owner。

注意：SQL 文本里不得出现带 ``%`` 的字面量。LIKE 后缀一律走
``:head_suffix`` / ``:manager_suffix`` 绑定参数，否则 ``sa.text`` 会把
``'%:head'`` 中的 ``head`` 登记成 bindparam（执行时报 InvalidRequestError），
且 psycopg2 的 pyformat 还需要额外转义裸 ``%``。
"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0220_permission_role_owner_delegate"
down_revision: str | None = "0216_core_workbench_todo_reads_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# 与 GRANT_ACTIVE / GRANT_DISABLED 对齐（app/platform/permission/models.py）。
_ACTIVE = "active"
_DISABLED = "disabled"

# 唯一退役判据定义点：三条语句全部复用，避免口径漂移。
# - is_builtin：防止误伤人工创建、code 恰好以 :head / :manager 结尾的岗位角色；
# - role_type 并集：覆盖 role_type 与 code 不同步的历史脏数据。
_RETIRED_SQL = """
    is_builtin
    AND is_deleted = false
    AND status = :active
    AND (role_type IN ('head', 'manager')
         OR code LIKE :head_suffix
         OR code LIKE :manager_suffix)
"""

_RETIRED_PARAMS = {
    "active": _ACTIVE,
    "head_suffix": "%:head",
    "manager_suffix": "%:manager",
}

# 人工恢复**模板**：仅用于 psql / 数据库客户端人工执行，不参与自动化。
# - 占位符 <CONFIRMED_ROLE_IDS> 必须由运维按 upgrade 日志清单人工替换；
# - 禁止包进 sa.text() 执行（'%:head' 会被登记为 bindparam）；
# - 第 3 步会连带复活「迁移前就已停用」的授权行，执行前必须核对停用时间。
_RESTORE_SQL = """
-- 1) 核对清单（与 upgrade 日志的 code 列表逐条比对，勿全量执行）
SELECT id, code, module_code, role_type, status
  FROM permission.roles
 WHERE is_builtin AND is_deleted = false AND status = 'disabled'
   AND (role_type IN ('head', 'manager')
        OR code LIKE '%:head' OR code LIKE '%:manager');
-- 2) 恢复角色（<CONFIRMED_ROLE_IDS> 用第 1 步人工确认的 id 替换）
UPDATE permission.roles SET status = 'active'
 WHERE is_builtin AND is_deleted = false AND status = 'disabled'
   AND id IN (<CONFIRMED_ROLE_IDS>);
-- 3) 恢复授权（会复活同一角色下迁移前就已停用的授权，须先核对）
UPDATE permission.user_role_grants SET status = 'active'
 WHERE is_deleted = false AND status = 'disabled'
   AND role_id IN (<CONFIRMED_ROLE_IDS>);
"""


def _stmt(sql: str, **extra: str) -> sa.sql.elements.TextClause:
    """把 SQL 文本与唯一一组参数值绑到一起：每条语句只调用一次 bindparams。"""
    return sa.text(sql).bindparams(**{**_RETIRED_PARAMS, **extra})


def retired_roles_stmt() -> sa.sql.elements.TextClause:
    """只读命中清单（日志可直接作为运维重新指派清单）。"""
    return _stmt("SELECT id, code, module_code, role_type FROM permission.roles WHERE " + _RETIRED_SQL)


def disable_grants_stmt() -> sa.sql.elements.TextClause:
    """停用退役角色名下的 active 授权（先授权、后角色）。"""
    return _stmt(
        "UPDATE permission.user_role_grants SET status = :disabled "
        "WHERE status = :active AND is_deleted = false AND role_id IN "
        "(SELECT id FROM permission.roles WHERE " + _RETIRED_SQL + ")",
        disabled=_DISABLED,
    )


def disable_roles_stmt() -> sa.sql.elements.TextClause:
    """停用退役角色本身。"""
    return _stmt(
        "UPDATE permission.roles SET status = :disabled WHERE " + _RETIRED_SQL,
        disabled=_DISABLED,
    )


def upgrade() -> None:
    bind = op.get_bind()

    # 1) 只读命中清单
    rows = bind.execute(retired_roles_stmt()).mappings().all()
    logger.warning("0203 命中历史内置角色 %s 行: %s", len(rows), [row["code"] for row in rows])
    if not rows:
        return

    # 2) 先停授权（避免中间态读到「角色还在 / 授权已断」）
    n_grant = bind.execute(disable_grants_stmt()).rowcount
    logger.warning("0203 停用授权 %s 行", n_grant)

    # 3) 再停角色
    n_role = bind.execute(disable_roles_stmt()).rowcount
    logger.warning("0203 停用角色 %s 行", n_role)


def downgrade() -> None:
    """不自动恢复：退役是一次性治理动作，误停用应由管理员确认后人工恢复。"""
    logger.warning("0203 downgrade 为 no-op；人工恢复模板（需替换占位符）：\n%s", _RESTORE_SQL)
