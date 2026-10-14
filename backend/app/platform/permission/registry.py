"""权限代码注册表（唯一权威）。

所有权限码、内置角色、接口绑定的定义都集中在此。应用启动时由
`sync_registry`（见 service.py）把这些声明幂等地同步进 DB 的只读镜像表。

规则（对照《权限体系设计对比报告》第六节）：
- 权限码一经发布不可删除、不可复用；下线只能标记 deprecated（退役）。
- 每个受保护接口必须在此登记 api_bindings（方法 + 路由模板），未登记 → 403。
- 新增权限码请在此追加，不要直接改 DB。
"""

from dataclasses import dataclass

from app.shared.module_registry import BUSINESS_MODULES

# ── 动作集合 ──────────────────────────────────────────────────────

# 业务资源动作（固定集合，业务模块新增权限码必须从此取值）
BUSINESS_ACTIONS: tuple[str, ...] = (
    "read",
    "create",
    "update",
    "delete",
    "submit",
    "approve",
    "reject",
    "export",
    "import",
)

# 平台管理动作
PLATFORM_ACTIONS: tuple[str, ...] = ("read", "manage")


# ── 声明结构 ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class PermissionDef:
    code: str
    name: str
    module: str
    resource: str
    action: str
    description: str = ""


@dataclass(frozen=True)
class RoleDef:
    code: str
    name: str
    category: str
    module_code: str | None
    description: str
    is_superuser: bool = False


@dataclass(frozen=True)
class ApiBindingDef:
    permission_code: str
    method: str
    route_template: str
    scope_required: bool = False


# ── 平台权限码 ────────────────────────────────────────────────────

PLATFORM_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef("platform:user:read", "查看用户", "platform", "user", "read"),
    PermissionDef("platform:user:manage", "管理用户", "platform", "user", "manage"),
    PermissionDef("platform:role:read", "查看角色", "platform", "role", "read"),
    PermissionDef("platform:role:manage", "管理角色", "platform", "role", "manage"),
    PermissionDef("platform:permission:read", "查看权限目录", "platform", "permission", "read"),
    PermissionDef("platform:grant:read", "查看授权", "platform", "grant", "read"),
    PermissionDef("platform:grant:manage", "管理授权", "platform", "grant", "manage"),
    PermissionDef("platform:config:read", "查看平台配置", "platform", "config", "read"),
    PermissionDef("platform:config:manage", "管理平台配置", "platform", "config", "manage"),
    PermissionDef("platform:audit:read", "查看审计日志", "platform", "audit", "read"),
    PermissionDef("platform:api-binding:read", "查看接口绑定登记簿", "platform", "api-binding", "read"),
    PermissionDef("platform:ops:read", "查看系统运维", "platform", "ops", "read"),
    PermissionDef("platform:ops:manage", "系统运维操作", "platform", "ops", "manage"),
)


# ── 管理界面展示用中文名（仅渲染用，不参与权限判定）──────────────

PLATFORM_DOMAIN_LABEL = "平台管理"

RESOURCE_LABELS: dict[str, str] = {
    "user": "用户管理",
    "role": "角色管理",
    "permission": "权限目录",
    "grant": "授权管理",
    "config": "平台配置",
    "audit": "审计日志",
    "api-binding": "接口绑定",
    "ops": "系统运维",
}

# ── 业务模块访问权限码（菜单级：每个模块 1 个）─────────────────────
#
# 粒度刻意做粗：只控制「模块菜单是否可见 + 模块页面能否进入」。
# 具体接口/操作权限（`<module>:<resource>:<action>`）后续按需追加 ——
# 两层**正交**：菜单认这里的粗码，接口认细码，细化时无需改菜单配置。
#
# 模块清单一律取自 `BUSINESS_MODULES`（唯一权威），不手抄，避免与前端菜单漂移。
BUSINESS_MODULE_PERMISSIONS: tuple[PermissionDef, ...] = tuple(
    PermissionDef(
        code=f"{module.code}:module:read",
        name=f"访问{module.name}",
        module=module.code,
        resource="module",
        action="read",
        description="模块菜单可见性与页面准入（接口级权限后续追加）",
    )
    for module in BUSINESS_MODULES
)


# 全部权限码（业务模块接入存量接口时，把业务权限码合并进来即可，权限树会自动生长）
ALL_PERMISSIONS: tuple[PermissionDef, ...] = PLATFORM_PERMISSIONS + BUSINESS_MODULE_PERMISSIONS


# ── 内置角色 ──────────────────────────────────────────────────────
# 内置角色**只保留超级管理员**（2026-10-13 按需求精简）：
# 原先的 48 个模块角色（{module}:{admin|operator|approver|viewer}）与
# permission_admin / config_admin 已下线，不再由注册表声明。
#
# 需要其他角色时，由管理员在「权限管理 → 角色管理」里**自建**（可勾选权限码）。

PLATFORM_ROLES: tuple[RoleDef, ...] = (
    RoleDef(
        code="super_admin",
        name="超级管理员",
        category="platform",
        module_code=None,
        description="拥有全部权限，判定时直接放行",
        is_superuser=True,
    ),
)

ALL_BUILTIN_ROLES: tuple[RoleDef, ...] = PLATFORM_ROLES


# ── 内置角色 → 权限码映射 ──────────────────────────────────────────
# super_admin 通过 is_superuser 直接放行，不在此绑定权限码。
# 其余内置角色已下线（2026-10-13），故此处为空：其他角色的权限由管理员
# 自建角色时在权限树上勾选，写入 permission.role_permissions。

BUILTIN_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {}


# ── 接口绑定登记簿（首批：平台管理接口）────────────────────────────
# route_template 不含参数值，路径参数用 {name} 占位，与 FastAPI 路由模板对齐。

API_BINDINGS: tuple[ApiBindingDef, ...] = (
    # 用户管理
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/users"),
    ApiBindingDef("platform:user:manage", "POST", "/api/v1/identity/users"),
    ApiBindingDef("platform:user:manage", "PUT", "/api/v1/identity/users/{id}"),
    ApiBindingDef("platform:user:manage", "POST", "/api/v1/identity/users/{id}/reset-password"),
    ApiBindingDef("platform:user:manage", "POST", "/api/v1/identity/users/{id}/bind-feishu"),
    ApiBindingDef("platform:user:manage", "DELETE", "/api/v1/identity/users/{id}/bind-feishu"),
    # 组织架构 / 人员名单（平台用户读权限即可）
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/departments"),
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/departments/{dept_id}"),
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/personnel"),
    # 登录记录（审计类）
    ApiBindingDef("platform:audit:read", "GET", "/api/v1/identity/login-logs"),
    # 操作审计
    ApiBindingDef("platform:audit:read", "GET", "/api/v1/audit/logs"),
    # Livzon 助手飞书配置与通讯录同步
    ApiBindingDef("platform:config:read", "GET", "/api/v1/identity/feishu-config"),
    ApiBindingDef("platform:config:manage", "PUT", "/api/v1/identity/feishu-config"),
    ApiBindingDef("platform:config:manage", "POST", "/api/v1/identity/feishu-config/test"),
    ApiBindingDef("platform:config:manage", "POST", "/api/v1/identity/sync/departments"),
    ApiBindingDef("platform:config:manage", "POST", "/api/v1/identity/sync/members"),
    ApiBindingDef("platform:config:manage", "POST", "/api/v1/identity/sync/all"),
    # 角色管理
    ApiBindingDef("platform:role:read", "GET", "/api/v1/permission/roles"),
    ApiBindingDef("platform:role:manage", "POST", "/api/v1/permission/roles"),
    ApiBindingDef("platform:role:manage", "PUT", "/api/v1/permission/roles/{id}"),
    ApiBindingDef("platform:role:manage", "DELETE", "/api/v1/permission/roles/{id}"),
    # 权限目录
    ApiBindingDef("platform:permission:read", "GET", "/api/v1/permission/permissions"),
    # 权限树只服务于「角色管理」勾选权限，跟随 role:read（与端点 require_permission 对齐）
    ApiBindingDef("platform:role:read", "GET", "/api/v1/permission/tree"),
    ApiBindingDef("platform:api-binding:read", "GET", "/api/v1/permission/api-bindings"),
    # 授权管理
    ApiBindingDef("platform:grant:read", "GET", "/api/v1/permission/grants"),
    ApiBindingDef("platform:grant:manage", "POST", "/api/v1/permission/grants"),
    ApiBindingDef("platform:grant:manage", "PUT", "/api/v1/permission/grants/{id}"),
    ApiBindingDef("platform:grant:manage", "DELETE", "/api/v1/permission/grants/{id}"),
    # 当前用户权限（登录用户自取）
    ApiBindingDef("platform:permission:read", "GET", "/api/v1/permission/my-permissions"),
    # 系统运维
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/health"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/info"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/resources"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/redis"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/redis/keys"),
    ApiBindingDef("platform:ops:manage", "DELETE", "/api/v1/system/redis/keys"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/scheduled-tasks"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/modules"),
    # API 启停开关
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/api-routes"),
    ApiBindingDef("platform:ops:manage", "PUT", "/api/v1/system/api-routes/switch"),
    # 日志管理
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/logs"),
    ApiBindingDef("platform:ops:manage", "DELETE", "/api/v1/system/logs"),
    # 数据库信息（只读：概览 + 表清单 + 表字段结构）
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/db/tables"),
    ApiBindingDef(
        "platform:ops:read",
        "GET",
        "/api/v1/system/db/tables/{schema}/{table}/columns",
    ),
    # 菜单栏管理（显隐 / 权重 / 权限绑定 / 自定义菜单项）
    ApiBindingDef("platform:ops:manage", "PUT", "/api/v1/system/menus/config"),
)


# ── 登录入口 / 当前用户自取（豁免绑定兜底）─────────────────────────
# 这两类接口无法绑定权限码，若按「未登记即 403」处理，开启
# `PERMISSION_ENFORCE_ENABLED` 后登录会整体挂掉：
# - 登录入口（auth/*）：调用方还没登录，不可能持有权限码；
# - 当前用户自取（me）：只要求「已登录」，权限判定交给路由自身的 require_user。
# 因此它们只做豁免登记，不参与权限绑定。
EXEMPT_ROUTES: tuple[tuple[str, str], ...] = (
    ("GET", "/api/v1/identity/auth/login"),
    ("GET", "/api/v1/identity/auth/callback"),
    ("GET", "/api/v1/identity/auth/logout"),
    ("POST", "/api/v1/identity/auth/local/login"),
    ("POST", "/api/v1/identity/auth/test-login"),
    ("GET", "/api/v1/identity/me"),
    # 自助改密：任何登录用户都可能需要（尤其被标记「首登强制改密」时），
    # 不挂权限码，判定交给路由自身的 require_user
    ("POST", "/api/v1/identity/me/password"),
    # 菜单栏配置读取：每个登录用户的导航渲染都要读，只要求已登录（写操作用 ops:manage）
    ("GET", "/api/v1/system/menus/config"),
)


# ── 便捷索引 ──────────────────────────────────────────────────────

PERMISSIONS_BY_CODE: dict[str, PermissionDef] = {p.code: p for p in ALL_PERMISSIONS}
ROLES_BY_CODE: dict[str, RoleDef] = {r.code: r for r in ALL_BUILTIN_ROLES}
BINDINGS_BY_ROUTE: dict[tuple[str, str], ApiBindingDef] = {(b.method, b.route_template): b for b in API_BINDINGS}

# 受保护路由前缀：这些前缀下的请求必须已登记绑定，否则 403
PROTECTED_ROUTE_PREFIXES: tuple[str, ...] = tuple(
    f"/api/v1/{module.path.lstrip('/')}" for module in BUSINESS_MODULES
) + (
    "/api/v1/permission",
    "/api/v1/identity",
    "/api/v1/system",
    "/api/v1/audit",
)


def is_protected_route(path: str) -> bool:
    """判断路由是否属于受保护前缀。"""
    return any(path == prefix or path.startswith(prefix + "/") for prefix in PROTECTED_ROUTE_PREFIXES)
