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
    # ── research（研发管理）资源 ──
    "project": "研发项目",
    "track": "研究跟踪",
    "initiation": "立项",
    "route": "工艺路线",
    "experiment-log": "实验日志",
    "pilot-study": "中试研究",
    "pilot-workflow": "中试工作流",
    "process-validation": "工艺验证",
    "registration-filing": "注册申报",
    "deliverable-template": "交付物模板",
    "stage-deliverable": "阶段交付物",
    "optimization": "工艺优化",
    "ich": "ICH 分析",
    "literature": "文献分析",
    "report": "研发报告",
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


# ── 业务模块细粒度权限码：research（研发管理）─────────────────

RESEARCH_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef(
        "research:deliverable-template:create", "创建交付物模板", "research", "deliverable-template", "create"
    ),
    PermissionDef(
        "research:deliverable-template:delete", "删除交付物模板", "research", "deliverable-template", "delete"
    ),
    PermissionDef("research:deliverable-template:read", "查看交付物模板", "research", "deliverable-template", "read"),
    PermissionDef(
        "research:deliverable-template:update", "更新交付物模板", "research", "deliverable-template", "update"
    ),
    PermissionDef("research:experiment-log:create", "创建实验日志", "research", "experiment-log", "create"),
    PermissionDef("research:experiment-log:delete", "删除实验日志", "research", "experiment-log", "delete"),
    PermissionDef("research:experiment-log:export", "导出实验日志", "research", "experiment-log", "export"),
    PermissionDef("research:experiment-log:read", "查看实验日志", "research", "experiment-log", "read"),
    PermissionDef("research:experiment-log:update", "更新实验日志", "research", "experiment-log", "update"),
    PermissionDef("research:ich:create", "创建ICH 分析", "research", "ich", "create"),
    PermissionDef("research:ich:delete", "删除ICH 分析", "research", "ich", "delete"),
    PermissionDef("research:ich:read", "查看ICH 分析", "research", "ich", "read"),
    PermissionDef("research:initiation:create", "创建立项", "research", "initiation", "create"),
    PermissionDef("research:initiation:delete", "删除立项", "research", "initiation", "delete"),
    PermissionDef("research:initiation:read", "查看立项", "research", "initiation", "read"),
    PermissionDef("research:initiation:update", "更新立项", "research", "initiation", "update"),
    PermissionDef("research:literature:create", "创建文献分析", "research", "literature", "create"),
    PermissionDef("research:optimization:create", "创建工艺优化", "research", "optimization", "create"),
    PermissionDef("research:optimization:delete", "删除工艺优化", "research", "optimization", "delete"),
    PermissionDef("research:optimization:read", "查看工艺优化", "research", "optimization", "read"),
    PermissionDef("research:optimization:update", "更新工艺优化", "research", "optimization", "update"),
    PermissionDef("research:pilot-study:create", "创建中试研究", "research", "pilot-study", "create"),
    PermissionDef("research:pilot-study:delete", "删除中试研究", "research", "pilot-study", "delete"),
    PermissionDef("research:pilot-study:read", "查看中试研究", "research", "pilot-study", "read"),
    PermissionDef("research:pilot-study:update", "更新中试研究", "research", "pilot-study", "update"),
    PermissionDef("research:pilot-workflow:approve", "审批中试工作流", "research", "pilot-workflow", "approve"),
    PermissionDef("research:pilot-workflow:create", "创建中试工作流", "research", "pilot-workflow", "create"),
    PermissionDef("research:pilot-workflow:delete", "删除中试工作流", "research", "pilot-workflow", "delete"),
    PermissionDef("research:pilot-workflow:read", "查看中试工作流", "research", "pilot-workflow", "read"),
    PermissionDef("research:pilot-workflow:submit", "提交/流转中试工作流", "research", "pilot-workflow", "submit"),
    PermissionDef("research:process-validation:create", "创建工艺验证", "research", "process-validation", "create"),
    PermissionDef("research:process-validation:delete", "删除工艺验证", "research", "process-validation", "delete"),
    PermissionDef("research:process-validation:read", "查看工艺验证", "research", "process-validation", "read"),
    PermissionDef("research:process-validation:update", "更新工艺验证", "research", "process-validation", "update"),
    PermissionDef("research:project:create", "创建研发项目", "research", "project", "create"),
    PermissionDef("research:project:delete", "删除研发项目", "research", "project", "delete"),
    PermissionDef("research:project:export", "导出研发项目", "research", "project", "export"),
    PermissionDef("research:project:read", "查看研发项目", "research", "project", "read"),
    PermissionDef("research:project:submit", "提交/流转研发项目", "research", "project", "submit"),
    PermissionDef("research:project:update", "更新研发项目", "research", "project", "update"),
    PermissionDef("research:registration-filing:create", "创建注册申报", "research", "registration-filing", "create"),
    PermissionDef("research:registration-filing:delete", "删除注册申报", "research", "registration-filing", "delete"),
    PermissionDef("research:registration-filing:read", "查看注册申报", "research", "registration-filing", "read"),
    PermissionDef("research:registration-filing:update", "更新注册申报", "research", "registration-filing", "update"),
    PermissionDef("research:report:create", "创建研发报告", "research", "report", "create"),
    PermissionDef("research:report:delete", "删除研发报告", "research", "report", "delete"),
    PermissionDef("research:report:read", "查看研发报告", "research", "report", "read"),
    PermissionDef("research:report:update", "更新研发报告", "research", "report", "update"),
    PermissionDef("research:route:create", "创建工艺路线", "research", "route", "create"),
    PermissionDef("research:route:delete", "删除工艺路线", "research", "route", "delete"),
    PermissionDef("research:route:read", "查看工艺路线", "research", "route", "read"),
    PermissionDef("research:route:update", "更新工艺路线", "research", "route", "update"),
    PermissionDef("research:stage-deliverable:create", "创建阶段交付物", "research", "stage-deliverable", "create"),
    PermissionDef("research:stage-deliverable:delete", "删除阶段交付物", "research", "stage-deliverable", "delete"),
    PermissionDef("research:stage-deliverable:read", "查看阶段交付物", "research", "stage-deliverable", "read"),
    PermissionDef("research:stage-deliverable:update", "更新阶段交付物", "research", "stage-deliverable", "update"),
    PermissionDef("research:track:create", "创建研究跟踪", "research", "track", "create"),
    PermissionDef("research:track:delete", "删除研究跟踪", "research", "track", "delete"),
    PermissionDef("research:track:export", "导出研究跟踪", "research", "track", "export"),
    PermissionDef("research:track:read", "查看研究跟踪", "research", "track", "read"),
    PermissionDef("research:track:update", "更新研究跟踪", "research", "track", "update"),
)


# 全部权限码（业务模块接入存量接口时，把业务权限码合并进来即可，权限树会自动生长）
ALL_PERMISSIONS: tuple[PermissionDef, ...] = PLATFORM_PERMISSIONS + BUSINESS_MODULE_PERMISSIONS + RESEARCH_PERMISSIONS


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
    # 会话管理（在线会话 / 踢下线）
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/sessions"),
    ApiBindingDef("platform:user:manage", "DELETE", "/api/v1/identity/sessions/{jti}"),
    ApiBindingDef("platform:user:manage", "DELETE", "/api/v1/identity/users/{id}/sessions"),
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
    ApiBindingDef("platform:grant:read", "GET", "/api/v1/permission/departments"),
    ApiBindingDef("platform:grant:read", "GET", "/api/v1/permission/grants"),
    ApiBindingDef("platform:grant:read", "GET", "/api/v1/permission/preview/{user_id}"),
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
    ApiBindingDef("platform:ops:manage", "PUT", "/api/v1/system/scheduled-tasks/{name}/toggle"),
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
    # create_module_router 注册的是 GET "/" → 实际路径带尾斜杠；中间件在路由重定向前执行，两种写法都要登记
    ApiBindingDef("research:module:read", "GET", "/api/v1/research"),
    ApiBindingDef("research:module:read", "GET", "/api/v1/research/"),
    ApiBindingDef(
        "research:deliverable-template:delete", "DELETE", "/api/v1/research/deliverable-templates/{template_id}"
    ),
    ApiBindingDef("research:experiment-log:delete", "DELETE", "/api/v1/research/experiment-logs/{log_id}"),
    ApiBindingDef("research:route:delete", "DELETE", "/api/v1/research/experiments/{exp_id}"),
    ApiBindingDef("research:track:delete", "DELETE", "/api/v1/research/findings/{finding_id}"),
    ApiBindingDef("research:ich:delete", "DELETE", "/api/v1/research/ich/records/{record_id}"),
    ApiBindingDef("research:initiation:delete", "DELETE", "/api/v1/research/initiations/{initiation_id}"),
    ApiBindingDef("research:optimization:delete", "DELETE", "/api/v1/research/optimizations/{optimization_id}"),
    ApiBindingDef("research:pilot-workflow:delete", "DELETE", "/api/v1/research/pilot/workflow/{workflow_id}"),
    ApiBindingDef("research:track:delete", "DELETE", "/api/v1/research/projects/tracks/{track_id}"),
    ApiBindingDef("research:project:delete", "DELETE", "/api/v1/research/projects/{project_id}"),
    ApiBindingDef("research:pilot-study:delete", "DELETE", "/api/v1/research/rd-pilot-studies/{study_id}"),
    ApiBindingDef(
        "research:process-validation:delete", "DELETE", "/api/v1/research/rd-process-validations/{validation_id}"
    ),
    ApiBindingDef("research:project:delete", "DELETE", "/api/v1/research/rd-projects/{project_id}"),
    ApiBindingDef(
        "research:registration-filing:delete", "DELETE", "/api/v1/research/rd-registration-filings/{filing_id}"
    ),
    ApiBindingDef(
        "research:stage-deliverable:delete", "DELETE", "/api/v1/research/rd-stage-deliverables/{deliverable_id}"
    ),
    ApiBindingDef("research:report:delete", "DELETE", "/api/v1/research/reports/{report_id}"),
    ApiBindingDef("research:route:delete", "DELETE", "/api/v1/research/routes/{route_id}"),
    ApiBindingDef("research:deliverable-template:read", "GET", "/api/v1/research/deliverable-templates"),
    ApiBindingDef("research:experiment-log:read", "GET", "/api/v1/research/experiment-logs"),
    ApiBindingDef("research:experiment-log:export", "GET", "/api/v1/research/export/experiment-logs"),
    ApiBindingDef("research:project:export", "GET", "/api/v1/research/export/projects"),
    ApiBindingDef("research:track:export", "GET", "/api/v1/research/export/tracks"),
    ApiBindingDef("research:ich:read", "GET", "/api/v1/research/ich/records"),
    ApiBindingDef("research:ich:read", "GET", "/api/v1/research/ich/records/{record_id}"),
    ApiBindingDef("research:initiation:read", "GET", "/api/v1/research/initiations"),
    ApiBindingDef("research:optimization:read", "GET", "/api/v1/research/optimizations"),
    ApiBindingDef("research:optimization:read", "GET", "/api/v1/research/optimizations/{optimization_id}"),
    ApiBindingDef("research:pilot-study:read", "GET", "/api/v1/research/pilot-studies"),
    ApiBindingDef("research:pilot-workflow:read", "GET", "/api/v1/research/pilot/workflow"),
    ApiBindingDef("research:pilot-workflow:read", "GET", "/api/v1/research/pilot/workflow/{workflow_id}"),
    ApiBindingDef(
        "research:pilot-workflow:read", "GET", "/api/v1/research/pilot/workflow/{workflow_id}/steps/{step_id}"
    ),
    ApiBindingDef("research:process-validation:read", "GET", "/api/v1/research/process-validations"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects/{project_id}"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects/{project_id}/milestones"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects/{project_id}/stages"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects/{project_id}/tracks"),
    ApiBindingDef("research:pilot-study:read", "GET", "/api/v1/research/rd-pilot-studies"),
    ApiBindingDef("research:process-validation:read", "GET", "/api/v1/research/rd-process-validations"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/rd-projects"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/rd-projects/{project_id}"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/rd-projects/{project_id}/transition-check"),
    ApiBindingDef("research:registration-filing:read", "GET", "/api/v1/research/rd-registration-filings"),
    ApiBindingDef("research:stage-deliverable:read", "GET", "/api/v1/research/rd-stage-deliverables"),
    ApiBindingDef("research:stage-deliverable:read", "GET", "/api/v1/research/rd-stage-deliverables/{deliverable_id}"),
    ApiBindingDef(
        "research:stage-deliverable:read", "GET", "/api/v1/research/rd-stage-deliverables/{deliverable_id}/download"
    ),
    ApiBindingDef("research:registration-filing:read", "GET", "/api/v1/research/registration-filings"),
    ApiBindingDef("research:report:read", "GET", "/api/v1/research/reports"),
    ApiBindingDef("research:route:read", "GET", "/api/v1/research/routes"),
    ApiBindingDef("research:route:read", "GET", "/api/v1/research/routes/{route_id}"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/stats/overview"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/stats/project-progress"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks/{track_id}"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks/{track_id}/conclusion-versions"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks/{track_id}/conclusions"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks/{track_id}/findings"),
    ApiBindingDef("research:deliverable-template:create", "POST", "/api/v1/research/deliverable-templates"),
    ApiBindingDef("research:optimization:create", "POST", "/api/v1/research/edbo/generate-scope"),
    ApiBindingDef("research:optimization:create", "POST", "/api/v1/research/edbo/optimize"),
    ApiBindingDef("research:experiment-log:create", "POST", "/api/v1/research/experiment-logs"),
    ApiBindingDef("research:report:create", "POST", "/api/v1/research/generate-report"),
    ApiBindingDef("research:ich:create", "POST", "/api/v1/research/ich/analyze"),
    ApiBindingDef("research:ich:create", "POST", "/api/v1/research/ich/q3c/analyze"),
    ApiBindingDef("research:initiation:create", "POST", "/api/v1/research/initiations"),
    ApiBindingDef("research:literature:create", "POST", "/api/v1/research/literature/analyze"),
    ApiBindingDef("research:optimization:create", "POST", "/api/v1/research/optimizations"),
    ApiBindingDef("research:pilot-study:create", "POST", "/api/v1/research/pilot-studies"),
    ApiBindingDef("research:pilot-workflow:create", "POST", "/api/v1/research/pilot/workflow"),
    ApiBindingDef("research:pilot-workflow:approve", "POST", "/api/v1/research/pilot/workflow/{workflow_id}/approve"),
    ApiBindingDef("research:pilot-workflow:submit", "POST", "/api/v1/research/pilot/workflow/{workflow_id}/start"),
    ApiBindingDef("research:pilot-workflow:create", "POST", "/api/v1/research/pilot/workflow/{workflow_id}/upload"),
    ApiBindingDef("research:process-validation:create", "POST", "/api/v1/research/process-validations"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/projects"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/projects/{project_id}/milestones"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/projects/{project_id}/stages"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/projects/{project_id}/tracks"),
    ApiBindingDef("research:pilot-study:create", "POST", "/api/v1/research/rd-pilot-studies"),
    ApiBindingDef("research:process-validation:create", "POST", "/api/v1/research/rd-process-validations"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/rd-projects"),
    ApiBindingDef("research:project:submit", "POST", "/api/v1/research/rd-projects/{project_id}/transition"),
    ApiBindingDef("research:registration-filing:create", "POST", "/api/v1/research/rd-registration-filings"),
    ApiBindingDef("research:stage-deliverable:create", "POST", "/api/v1/research/rd-stage-deliverables"),
    ApiBindingDef(
        "research:stage-deliverable:create", "POST", "/api/v1/research/rd-stage-deliverables/{deliverable_id}/upload"
    ),
    ApiBindingDef("research:registration-filing:create", "POST", "/api/v1/research/registration-filings"),
    ApiBindingDef("research:report:create", "POST", "/api/v1/research/reports"),
    ApiBindingDef("research:route:create", "POST", "/api/v1/research/routes"),
    ApiBindingDef("research:route:create", "POST", "/api/v1/research/routes/{route_id}/experiments"),
    ApiBindingDef("research:track:create", "POST", "/api/v1/research/tracks/{track_id}/conclusion-versions"),
    ApiBindingDef("research:track:create", "POST", "/api/v1/research/tracks/{track_id}/conclusions"),
    ApiBindingDef("research:track:create", "POST", "/api/v1/research/tracks/{track_id}/findings"),
    ApiBindingDef(
        "research:deliverable-template:update", "PUT", "/api/v1/research/deliverable-templates/{template_id}"
    ),
    ApiBindingDef("research:experiment-log:update", "PUT", "/api/v1/research/experiment-logs/{log_id}"),
    ApiBindingDef("research:route:update", "PUT", "/api/v1/research/experiments/{exp_id}"),
    ApiBindingDef("research:track:update", "PUT", "/api/v1/research/findings/{finding_id}"),
    ApiBindingDef("research:initiation:update", "PUT", "/api/v1/research/initiations/{initiation_id}"),
    ApiBindingDef("research:optimization:update", "PUT", "/api/v1/research/optimizations/{optimization_id}"),
    ApiBindingDef("research:pilot-study:update", "PUT", "/api/v1/research/pilot-studies/{study_id}"),
    ApiBindingDef("research:process-validation:update", "PUT", "/api/v1/research/process-validations/{validation_id}"),
    ApiBindingDef("research:project:update", "PUT", "/api/v1/research/projects/milestones/{milestone_id}"),
    ApiBindingDef("research:project:update", "PUT", "/api/v1/research/projects/stages/{record_id}"),
    ApiBindingDef("research:track:update", "PUT", "/api/v1/research/projects/tracks/{track_id}"),
    ApiBindingDef("research:project:update", "PUT", "/api/v1/research/projects/{project_id}"),
    ApiBindingDef("research:pilot-study:update", "PUT", "/api/v1/research/rd-pilot-studies/{study_id}"),
    ApiBindingDef(
        "research:process-validation:update", "PUT", "/api/v1/research/rd-process-validations/{validation_id}"
    ),
    ApiBindingDef("research:project:update", "PUT", "/api/v1/research/rd-projects/{project_id}"),
    ApiBindingDef("research:registration-filing:update", "PUT", "/api/v1/research/rd-registration-filings/{filing_id}"),
    ApiBindingDef(
        "research:stage-deliverable:update", "PUT", "/api/v1/research/rd-stage-deliverables/{deliverable_id}"
    ),
    ApiBindingDef("research:registration-filing:update", "PUT", "/api/v1/research/registration-filings/{filing_id}"),
    ApiBindingDef("research:report:update", "PUT", "/api/v1/research/reports/{report_id}"),
    ApiBindingDef("research:route:update", "PUT", "/api/v1/research/routes/{route_id}"),
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


# ── 按模块灰度强制 ────────────────────────────────────────────────
# `PERMISSION_ENFORCE_MODULES`（config.py）允许只对已完成绑定的模块开强制，
# 未完成的模块暂不受兜底影响（接入一个开一个，避免一刀切 403）。

# 路径前缀 → 模块码（含平台域伪模块码，用于灰度集合取值）
_PREFIX_TO_MODULE: dict[str, str] = {
    **{f"/api/v1/{m.path.lstrip('/')}": m.code for m in BUSINESS_MODULES},
    "/api/v1/permission": "permission",
    "/api/v1/identity": "identity",
    "/api/v1/system": "system",
    "/api/v1/audit": "audit",
}

# 灰度集合可用模块码全集（校验配置拼写用）
ENFORCEABLE_MODULE_CODES: frozenset[str] = frozenset(_PREFIX_TO_MODULE.values())

# ── 已完成接入的模块（CI 完整性门禁范围）─────────────────────────
# 模块的全部接口绑定登记完成后，把模块码加到这里：
# - scripts/ci/check_permissions.py 会对它执行完整性校验
#   （每个路由都有绑定或豁免、每个 require_permission 码都存在）；
# - 此后才允许把该模块码加入部署配置的 PERMISSION_ENFORCE_MODULES 开强制。
ENFORCE_READY_MODULES: tuple[str, ...] = ("research",)


def module_for_path(path: str) -> str | None:
    """反查请求路径所属模块码；非受保护路径返回 None。"""
    for prefix, code in _PREFIX_TO_MODULE.items():
        if path == prefix or path.startswith(prefix + "/"):
            return code
    return None


def is_enforced_route(path: str, enabled_modules: frozenset[str]) -> bool:
    """该路径是否处于强制兜底范围：受保护 且 （灰度集合为空=全部 / 或所属模块在集合内）。"""
    code = module_for_path(path)
    if code is None:
        return False
    return not enabled_modules or code in enabled_modules
