"""为 2026-10-23 新增的细粒度权限码补齐角色授权（幂等、可预览）。

背景
----
改造前 safety 模块 220 个接口统一挂在 `safety:module:read` 下，申报资料写作
35 个接口统一挂在 `registration:dossier:read` 下（读权限即可写）。本次按
「资源 + 动作」拆分：

- `safety:<resource>:read` / `safety:<resource>:manage`
- `registration:dossier:read / create / update / delete`

不补授权的话，上线后所有非超管账号在 safety / 申报资料写作上会立刻 403。

策略
----
默认 `--preserve-behavior`（等价改造前能力，先不改变业务可用性）：

- 持有 `safety:module:read` 的角色 → 补齐全部 safety 细码（含 `:manage`）；
- 持有 `registration:dossier:read` 的角色 → 补齐 dossier 的写码。

`--read-only`：只补 `:read`，不补写码。适合「先收紧再逐个授写权限」的节奏，
但上线前必须确认这些角色确实不需要写操作，否则相关按钮会 403。

用法
----
    uv run python scripts/migration/backfill_permission_grants_20261023.py            # 只预览
    uv run python scripts/migration/backfill_permission_grants_20261023.py --apply    # 实际写入
    uv run python scripts/migration/backfill_permission_grants_20261023.py --read-only --apply
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import async_session_factory
from app.platform.permission.registry import PERMISSIONS_BY_CODE, SAFETY_PERMISSIONS
from app.platform.permission.repository import RoleRepository

SAFETY_MODULE_CODE = "safety:module:read"
DOSSIER_MODULE_CODE = "registration:dossier:read"
DOSSIER_WRITE_CODES = tuple(
    code for code in PERMISSIONS_BY_CODE if code.startswith("registration:dossier:") and not code.endswith(":read")
)


def _safety_codes(*, read_only: bool) -> list[str]:
    return sorted(p.code for p in SAFETY_PERMISSIONS if p.action == "read" or (not read_only and p.action == "manage"))


async def main(apply: bool, read_only: bool) -> int:
    safety_targets = _safety_codes(read_only=read_only)
    repo = RoleRepository()
    planned = 0
    async with async_session_factory() as db:
        roles = await repo.list_roles(db)
        for role in roles:
            current = set(await repo.list_role_permission_codes(db, role.id))
            added: set[str] = set()
            if SAFETY_MODULE_CODE in current:
                added |= set(safety_targets) - current
            if DOSSIER_MODULE_CODE in current and not read_only:
                added |= set(DOSSIER_WRITE_CODES) - current
            if not added:
                continue
            planned += 1
            print(f"[{'写入' if apply else '预览'}] {role.code}（{role.name}）新增 {len(added)} 个权限码")
            for code in sorted(added):
                print(f"    + {code}")
            if apply:
                await repo.set_role_permissions(db, role.id, sorted(current | added))
        if apply:
            await db.commit()
    verb = "已写入" if apply else "待写入（加 --apply 生效）"
    print(f"\n共 {planned} 个角色需要调整，{verb}。")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="补齐 2026-10-23 新增权限码的角色授权")
    parser.add_argument("--apply", action="store_true", help="实际写入数据库（默认只预览）")
    parser.add_argument("--read-only", action="store_true", help="只补只读码，不补写码")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(apply=args.apply, read_only=args.read_only)))
