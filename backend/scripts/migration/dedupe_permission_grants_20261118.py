"""清洗 permission.user_role_grants 的历史重复授权（幂等、可预览）。

背景
----
`user_role_grants` 历史上没有「同一人同一角色只能有一条活跃授权」的约束，
重复点两次「新建授权」就会产生两条 active 行。委派式权限管理引入了该约束
（迁移 0130 的部分唯一索引 `uq_permission_user_role_grants_active`），
若库里仍有重复行，索引创建失败、且会出现「删一条还剩一条、权限没回收」的现象。

策略
----
同一 (user_id, role_id) 存在多条 active 行时，只保留 (created_at, id) 最大的那条，
其余置为 `status='disabled'`。停用而不是软删：保留审计痕迹，必要时可人工恢复。

迁移 0130 在创建索引前也会执行同样的清理（保证顺序），本脚本用于：
- 上线前在 UAT / 生产提前自查与清理；
- 迁移后再跑一次校验（幂等，重复执行无副作用）。

用法
----
    uv run python scripts/migration/dedupe_permission_grants_20261118.py            # 只预览
    uv run python scripts/migration/dedupe_permission_grants_20261118.py --apply    # 实际写入
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text

from app.core.database import async_session_factory

# 待停用的重复行（保留每组最新一条）
_SELECT_DUPLICATES = text(
    """
    SELECT g.id, g.user_id, g.role_id, g.created_at
    FROM permission.user_role_grants AS g
    WHERE g.is_deleted = false
      AND g.status = 'active'
      AND EXISTS (
          SELECT 1
          FROM permission.user_role_grants AS g2
          WHERE g2.user_id = g.user_id
            AND g2.role_id = g.role_id
            AND g2.is_deleted = false
            AND g2.status = 'active'
            AND (g2.created_at, g2.id) > (g.created_at, g.id)
      )
    ORDER BY g.user_id, g.role_id, g.created_at
    """
)

_DISABLE_DUPLICATES = text(
    """
    UPDATE permission.user_role_grants AS g
    SET status = 'disabled'
    WHERE g.is_deleted = false
      AND g.status = 'active'
      AND EXISTS (
          SELECT 1
          FROM permission.user_role_grants AS g2
          WHERE g2.user_id = g.user_id
            AND g2.role_id = g.role_id
            AND g2.is_deleted = false
            AND g2.status = 'active'
            AND (g2.created_at, g2.id) > (g.created_at, g.id)
      )
    """
)


async def main(apply: bool) -> None:
    async with async_session_factory() as db:
        rows = (await db.execute(_SELECT_DUPLICATES)).all()
        print(f"发现重复活跃授权 {len(rows)} 条（将被停用，每组保留最新一条）")
        for row in rows[:50]:
            print(f"  grant={row.id} user={row.user_id} role={row.role_id} created={row.created_at}")
        if len(rows) > 50:
            print(f"  ... 另有 {len(rows) - 50} 条")

        if not apply:
            print("\n预览模式，未写入。加 --apply 执行停用。")
            return
        if not rows:
            print("无需处理。")
            return

        result = await db.execute(_DISABLE_DUPLICATES)
        await db.commit()
        print(f"\n已停用 {result.rowcount} 条重复授权。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="清洗重复的用户角色授权")
    parser.add_argument("--apply", action="store_true", help="实际写入（默认只预览）")
    args = parser.parse_args()
    asyncio.run(main(args.apply))
