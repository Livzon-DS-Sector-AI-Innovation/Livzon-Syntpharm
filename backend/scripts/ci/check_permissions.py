"""权限注册表一致性校验（CI 门禁）。

校验 registry.py 声明的内部一致性：
1. 权限码唯一 + 格式正确（模块:资源:动作，三段）。
2. 内置角色 code 唯一。
3. 接口绑定 (method, route_template) 唯一。
4. 内置角色权限映射引用的角色 / 权限码都存在。

退出码：0 通过，非 0 失败（违反则 PR 不能合并）。

完整性门禁（registry.ENFORCE_READY_MODULES 列出的模块）：
- 该模块每个已挂载路由都必须登记绑定（或列入 EXEMPT_ROUTES 豁免）。
- 该模块代码里每个 require_permission("...") 引用的权限码都必须存在。

路由清单来源：导入 app.api.router 并生成 OpenAPI，按 module.path 前缀过滤。
v1 曾静态扫描模块目录并手工拼接前缀，把「文件里存在但从未 include 的路由」
和「子路由自带 prefix」（如 /hr/turnover-analysis 被拼成 /hr）都算成缺口，
实测 512 条报错全部是误报，真实缺口反而被埋掉。故改为以挂载结果为准；
导入失败时退回静态扫描并在 stderr 告警。
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
    ENFORCE_READY_MODULES,
    EXEMPT_ROUTES,
)
from app.shared.module_registry import MODULES_BY_CODE  # noqa: E402

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

# @router.get("/x") / @xxx_router.post("/y") 等路由装饰器
_ROUTE_RE = re.compile(r"@(?:[a-z_][a-z0-9_]*\.)?(?:router|app)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']*)[\"']")
# require_permission("code") 字面量
_REQUIRE_RE = re.compile(r"require_permission\(\s*[\"']([^\"']+)[\"']")
# 路由模板参数 {id} → 统一占位，用于模板结构比较
_PARAM_RE = re.compile(r"\{[^}]+\}")


def _normalize_template(template: str) -> str:
    return _PARAM_RE.sub("{}", template)


def _module_api_files(module_code: str) -> list[Path]:
    module_dir = _BACKEND_ROOT / "app" / "modules" / module_code
    return sorted(module_dir.rglob("*.py")) if module_dir.is_dir() else []


def _api_prefix() -> str:
    try:
        from app.core.config import get_settings

        return get_settings().API_V1_PREFIX.rstrip("/") or "/api/v1"
    except Exception:  # 配置不可用（本地裸跑脚本）时按默认前缀处理
        return "/api/v1"


def _mounted_routes() -> dict[str, frozenset[str]] | None:
    """返回 {归一化路由模板: {METHOD}}，取自真实挂载的 FastAPI 应用。

    无法构建应用（缺环境变量、依赖导入失败）时返回 None，调用方退回静态扫描。
    """
    try:
        from fastapi import FastAPI

        from app.api.router import api_router

        test_app = FastAPI()
        test_app.include_router(api_router, prefix=_api_prefix())
        paths = test_app.openapi().get("paths", {})
    except Exception as exc:  # 导入链任何失败都降级，但必须显式告警
        print(f"警告: 无法加载已挂载路由（{exc}），退回静态扫描，结果可能含未挂载路由", file=sys.stderr)
        return None
    mounted: dict[str, set[str]] = {}
    for path, item in paths.items():
        mounted.setdefault(_normalize_template(path.rstrip("/")), set()).update(m.upper() for m in item)
    return {path: frozenset(methods) for path, methods in mounted.items()}


def _scan_module_files_static(
    errors: list[str],
    module_code: str,
    module_prefix: str,
    files: list[Path],
    bound_templates: set[str],
    exempt_templates: set[str],
) -> None:
    """降级路径：静态扫描模块目录（可能包含未挂载路由，仅用于排查）。"""
    for py in files:
        text = py.read_text(encoding="utf-8")
        for method, route in _ROUTE_RE.findall(text):
            full = f"{module_prefix}{'' if route.startswith('/') else '/'}{route}".rstrip("/") or module_prefix
            norm = _normalize_template(full)
            if norm not in bound_templates and norm not in exempt_templates:
                errors.append(
                    f"模块 {module_code} 路由未登记绑定: {method.upper()} {full}（{py.relative_to(_BACKEND_ROOT)}）"
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

    # 2. 前端权限码常量表与后端 registry 对齐
    #    前端用 lib/permissions/codes.ts 的 PERM.* 控制按钮显示/隐藏；
    #    两边不一致会出现「按钮显示了但接口 403」或「有权限却看不到按钮」。
    codes_ts = Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "permissions" / "codes.ts"
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

    # 3. 内置角色 code 唯一
    seen_roles: set[str] = set()
    for r in ALL_BUILTIN_ROLES:
        if r.code in seen_roles:
            errors.append(f"角色 code 重复: {r.code}")
        seen_roles.add(r.code)

    # 4. 接口绑定唯一
    seen_bindings: set[tuple[str, str]] = set()
    for b in API_BINDINGS:
        key = (b.method, b.route_template)
        if key in seen_bindings:
            errors.append(f"接口绑定重复: {b.method} {b.route_template}")
        seen_bindings.add(key)

    # 5. 内置角色权限映射引用完整性
    role_codes = {r.code for r in ALL_BUILTIN_ROLES}
    for role_code, codes in BUILTIN_ROLE_PERMISSIONS.items():
        if role_code not in role_codes:
            errors.append(f"角色权限映射引用了不存在的角色: {role_code}")
        for code in codes:
            if code not in seen_codes:
                errors.append(f"角色 {role_code} 引用了未定义的权限码: {code}")

    # 6. 接口绑定引用的权限码必须存在
    for b in API_BINDINGS:
        if b.permission_code not in seen_codes:
            errors.append(f"接口绑定引用了未定义的权限码: {b.permission_code}（{b.method} {b.route_template}）")

    # 7. 就绪模块完整性门禁：每个已挂载路由有绑定（或豁免）、require_permission 可反查
    bound_pairs = {(b.method.upper(), _normalize_template(b.route_template.rstrip("/"))) for b in API_BINDINGS}
    exempt_pairs = {(m.upper(), _normalize_template(t.rstrip("/"))) for m, t in EXEMPT_ROUTES}
    mounted = _mounted_routes()
    for module_code in ENFORCE_READY_MODULES:
        module = MODULES_BY_CODE.get(module_code)
        if module is None:
            errors.append(f"ENFORCE_READY_MODULES 含未知模块码: {module_code}")
            continue
        module_prefix = f"{_api_prefix()}{module.path.rstrip('/')}"
        files = _module_api_files(module_code)
        if mounted is None:
            if not files:
                errors.append(f"就绪模块 {module_code} 未找到任何 api 文件: app/modules/{module_code}")
            else:
                _scan_module_files_static(
                    errors,
                    module_code,
                    module_prefix,
                    files,
                    {t for _, t in bound_pairs},
                    {t for _, t in exempt_pairs},
                )
        else:
            for route_path in sorted(mounted):
                if route_path != module_prefix and not route_path.startswith(f"{module_prefix}/"):
                    continue
                for method in sorted(mounted[route_path]):
                    if (method, route_path) in bound_pairs or (method, route_path) in exempt_pairs:
                        continue
                    errors.append(f"模块 {module_code} 路由未登记绑定: {method} {route_path}")
        # require_permission 字面量引用检查与路由是否挂载无关，始终静态扫
        for py in files:
            text = py.read_text(encoding="utf-8")
            for code in _REQUIRE_RE.findall(text):
                if code not in seen_codes:
                    errors.append(f"模块 {module_code} require_permission 引用未定义权限码: {code}（{py.name}）")

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
