"""清理已下线（status='disabled'）的角色及其残留授权映射。

幂等、可重复执行：再次运行时会跳过已删除的角色。
删除顺序：
1. 删除被下线角色的 role_permissions 行；
2. 删除被下线角色（前提：无任何 user_role_grants 占用，包括 disabled 状态）。

Usage:
    仅预览：uv run python scripts/migration/cleanup_disabled_roles.py --dry-run
    执行： uv run python scripts/migration/cleanup_disabled_roles.py
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import delete, select
from app.core.database import async_session_factory
from app.platform.permission.models import Role, RolePermission, UserRoleGrant


def _fmt(rows: list[tuple]) -> str:
    return "\n".join(f"  - {r[0]} ({r[1]} 行)" for r in rows)


async def main(dry_run: bool = False) -> None:
    async with async_session_factory() as db:
        # 1. 找出所有 disabled 角色
        result = await db.execute(select(Role.id, Role.code).where(Role.status == "disabled").order_by(Role.code))
        disabled = list(result.all())
        if not disabled:
            print("未发现 status='disabled' 的角色，无需清理")
            return

        print(f"发现 {len(disabled)} 个已下线角色：")
        for role_id, code in disabled:
            print(f"  - {code} ({role_id})")

        # 2. 检查 user_role_grants 占用（任何状态都算）
        unsafe: list[tuple[str, int]] = []
        deletable: list[tuple[object, str]] = []
        for role_id, code in disabled:
            count_result = await db.execute(
                select(UserRoleGrant.id).where(UserRoleGrant.role_id == role_id)
            )
            grants = list(count_result.scalars().all())
            if grants:
                unsafe.append((code, len(grants)))
            else:
                deletable.append((role_id, code))

        if unsafe:
            print("\n以下角色仍有用户授权占用，跳过删除：")
            print(_fmt(unsafe))

        if not deletable:
            print("\n没有可清理的角色")
            return

        print(f"\n可清理角色 {len(deletable)} 个")
        for role_id, code in deletable:
            print(f"  - {code}")

        # 3. 统计并清理 role_permissions
        rp_counts = []
        for role_id, code in deletable:
            cnt_res = await db.execute(select(RolePermission.id).where(RolePermission.role_id == role_id))
            cnt = len(list(cnt_res.scalars().all()))
            if cnt:
                rp_counts.append((code, cnt))

        if dry_run:
            print("\n[DRY-RUN] 将执行以下操作：")
            print(f"  删除 role_permissions 行：{sum(c for _, c in rp_counts)} 行")
            print(f"  删除 roles：{len(deletable)} 个")
            return

        if rp_counts:
            print(f"\n清理 role_permissions 残留：")
            print(_fmt(rp_counts))
            role_ids = [role_id for role_id, _ in deletable]
            await db.execute(delete(RolePermission).where(RolePermission.role_id.in_(role_ids)))

        # 4. 删除角色
        for role_id, code in deletable:
            await db.execute(delete(Role).where(Role.id == role_id))

        await db.commit()
        print(f"\n完成：删除角色 {len(deletable)} 个，清理 role_permissions {sum(c for _, c in rp_counts)} 行")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="清理已下线角色及其残留授权映射")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不删除")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
