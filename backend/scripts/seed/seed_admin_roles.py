"""预置「下级管理员」角色模板（幂等）。

超级管理员可在「授权管理」里直接把下面这些角色授给对应人员，实现分级管理：
- 账号管理员：只管账号（新建/启停/重置密码），不能碰角色与授权 → 无法自我提权；
- 权限管理员：管角色与授权（含数据范围），不能重置密码、不能看审计；
- 审计查看：只读登录记录与操作审计（GMP 合规审计角色，不给任何管理权）。

这三个是**普通自建角色**（非内置），管理员可自行修改；脚本按 code 幂等，重复执行不重复建。

Usage:
    uv run python scripts/seed/seed_admin_roles.py
"""

import asyncio

from app.core.database import async_session_factory
from app.platform.permission.models import GRANT_ACTIVE, Role
from app.platform.permission.repository import RoleRepository

ADMIN_ROLE_TEMPLATES: list[dict] = [
    {
        "code": "admin_account_manager",
        "name": "账号管理员",
        "description": "管理平台账号：新建 / 编辑 / 启停用户、生成 / 重置密码、解绑飞书。不可授权、不可改角色。",
        "permission_codes": ["platform:user:read", "platform:user:manage"],
    },
    {
        "code": "admin_permission_manager",
        "name": "权限管理员",
        "description": "管理角色与授权（含数据范围）；只读用户；不可重置密码、不可查看审计。",
        "permission_codes": [
            "platform:role:read",
            "platform:role:manage",
            "platform:permission:read",
            "platform:grant:read",
            "platform:grant:manage",
            "platform:api-binding:read",
            "platform:user:read",
        ],
    },
    {
        "code": "admin_auditor",
        "name": "审计查看",
        "description": "只读查看登录记录与操作审计（GMP 合规审计角色，不给任何管理权）。",
        "permission_codes": ["platform:audit:read"],
    },
]


async def main() -> None:
    async with async_session_factory() as db:
        role_repo = RoleRepository()
        created = 0
        skipped = 0
        for tpl in ADMIN_ROLE_TEMPLATES:
            if await role_repo.get_role_by_code(db, tpl["code"]) is not None:
                print(f"[SKIP] {tpl['name']}（{tpl['code']}）已存在")
                skipped += 1
                continue
            role = Role(
                code=tpl["code"],
                name=tpl["name"],
                category="platform",
                description=tpl["description"],
                is_builtin=False,
                is_superuser=False,
                status=GRANT_ACTIVE,
            )
            db.add(role)
            await db.flush()
            await role_repo.set_role_permissions(db, role.id, tpl["permission_codes"])
            created += 1
            print(f"[OK] 创建 {tpl['name']}（{tpl['code']}），权限 {len(tpl['permission_codes'])} 项")
        await db.commit()
        print(f"\n完成：新建 {created}，跳过 {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
