"""预置研发管理（research）模块角色模板（幂等）。

四档角色，对应研发团队的典型分工：
- research_admin：模块管理员，全资源全动作；
- research_editor：研发人员，可读写改删与提交流转，不可审批中试工作流；
- research_approver：审批角色，全资源只读 + 中试工作流审批；
- research_viewer：只读（含统计）。

所有角色都含 research:module:read（模块菜单可见 + 页面准入）。
这些是**普通自建角色**（非内置），管理员可自行修改；脚本按 code 幂等。

Usage:
    uv run python scripts/seed/seed_research_roles.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import async_session_factory
from app.platform.permission.models import GRANT_ACTIVE, Role
from app.platform.permission.registry import RESEARCH_PERMISSIONS
from app.platform.permission.repository import RoleRepository

_ALL_CODES = [p.code for p in RESEARCH_PERMISSIONS]
_MODULE_READ = "research:module:read"


def _codes(*, actions: set[str] | None = None, resources: set[str] | None = None) -> list[str]:
    """按动作/资源子集挑选 research 细码，且总是包含模块准入码。"""
    picked = [
        p.code
        for p in RESEARCH_PERMISSIONS
        if (actions is None or p.action in actions) and (resources is None or p.resource in resources)
    ]
    return [_MODULE_READ, *sorted(picked)]


RESEARCH_ROLE_TEMPLATES: list[dict] = [
    {
        "code": "research_admin",
        "name": "研发管理员",
        "description": "研发管理模块全部资源的查看与操作权限（含审批、导出）。",
        "permission_codes": [_MODULE_READ, *_ALL_CODES],
    },
    {
        "code": "research_editor",
        "name": "研发编辑",
        "description": "研发人员：全部资源可读写改删、提交流转、导出；不可审批中试工作流。",
        "permission_codes": _codes(actions={"read", "create", "update", "delete", "submit", "export"}),
    },
    {
        "code": "research_approver",
        "name": "研发审批",
        "description": "审批角色：全部资源只读 + 中试工作流审批。",
        "permission_codes": _codes(actions={"read"}) + ["research:pilot-workflow:approve"],
    },
    {
        "code": "research_viewer",
        "name": "研发查看",
        "description": "只读查看研发管理全部资源（含统计）。",
        "permission_codes": _codes(actions={"read"}),
    },
]


async def main() -> None:
    async with async_session_factory() as db:
        role_repo = RoleRepository()
        created = 0
        skipped = 0
        for tpl in RESEARCH_ROLE_TEMPLATES:
            if await role_repo.get_role_by_code(db, tpl["code"]) is not None:
                print(f"[SKIP] {tpl['name']}（{tpl['code']}）已存在")
                skipped += 1
                continue
            role = Role(
                code=tpl["code"],
                name=tpl["name"],
                category="module",
                module_code="research",
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
