"""权限注册表一致性校验（CI 门禁）。

校验 registry.py 声明的内部一致性：
1. 权限码唯一 + 格式正确（模块:资源:动作，三段）。
2. 内置角色 code 唯一。
3. 接口绑定 (method, route_template) 唯一。
4. 内置角色权限映射引用的角色 / 权限码都存在。

退出码：0 通过，非 0 失败（违反则 PR 不能合并）。

说明：业务权限码与存量接口绑定的「完整性」校验（每个 require_permission 都能
在 registry 找到、每个受保护路由都登记绑定）待存量接口接入后再启用。
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.platform.permission.registry import (  # noqa: E402
    ALL_BUILTIN_ROLES,
    ALL_PERMISSIONS,
    API_BINDINGS,
    BUILTIN_ROLE_PERMISSIONS,
)


def _check() -> list[str]:
    errors: list[str] = []

    # 1. 权限码唯一 + 格式
    seen_codes: set[str] = set()
    for p in ALL_PERMISSIONS:
        if p.code in seen_codes:
            errors.append(f"权限码重复: {p.code}")
        seen_codes.add(p.code)
        parts = p.code.split(":")
        if len(parts) != 3 or any(not part for part in parts):
            errors.append(f"权限码格式错误（应为 模块:资源:动作）: {p.code}")

    # 5. 前端权限码常量表与后端 registry 对齐
    #    前端用 lib/permissions/codes.ts 的 PERM.* 控制按钮显示/隐藏；
    #    两边不一致会出现「按钮显示了但接口 403」或「有权限却看不到按钮」。
    codes_ts = (
        Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "permissions" / "codes.ts"
    )
    if codes_ts.exists():
        frontend_codes = set(
            # 匹配任意「模块:资源:动作」权限码。此前只匹配 `platform:` 前缀，
            # 导致业务模块访问码（如 safety:module:read）漏检 —— 与 _sync_permissions 同源问题。
            re.findall(
                r"'([a-z][a-z0-9_-]*:[a-z0-9_-]+:[a-z0-9_-]+)'",
                codes_ts.read_text(encoding="utf-8"),
            )
        )
        backend_codes = {p.code for p in ALL_PERMISSIONS}
        missing_in_frontend = sorted(backend_codes - frontend_codes)
        extra_in_frontend = sorted(frontend_codes - backend_codes)
        if missing_in_frontend:
            errors.append(f"前端 lib/permissions/codes.ts 缺少权限码: {missing_in_frontend}")
        if extra_in_frontend:
            errors.append(f"前端 lib/permissions/codes.ts 存在后端未定义的权限码: {extra_in_frontend}")
    else:
        errors.append(f"未找到前端权限码常量文件: {codes_ts}")

    # 2. 内置角色 code 唯一
    seen_roles: set[str] = set()
    for r in ALL_BUILTIN_ROLES:
        if r.code in seen_roles:
            errors.append(f"角色 code 重复: {r.code}")
        seen_roles.add(r.code)

    # 3. 接口绑定唯一
    seen_bindings: set[tuple[str, str]] = set()
    for b in API_BINDINGS:
        key = (b.method, b.route_template)
        if key in seen_bindings:
            errors.append(f"接口绑定重复: {b.method} {b.route_template}")
        seen_bindings.add(key)

    # 4. 内置角色权限映射引用完整性
    role_codes = {r.code for r in ALL_BUILTIN_ROLES}
    for role_code, codes in BUILTIN_ROLE_PERMISSIONS.items():
        if role_code not in role_codes:
            errors.append(f"角色权限映射引用了不存在的角色: {role_code}")
        for code in codes:
            if code not in seen_codes:
                errors.append(f"角色 {role_code} 引用了未定义的权限码: {code}")

    return errors


def main() -> int:
    errors = _check()
    if errors:
        print("权限注册表校验失败:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(
        f"权限注册表校验通过: {len(ALL_PERMISSIONS)} 权限码, "
        f"{len(ALL_BUILTIN_ROLES)} 角色, {len(API_BINDINGS)} 接口绑定"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
