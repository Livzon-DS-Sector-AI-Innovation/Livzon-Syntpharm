"""权限体系常量（无外部依赖，供 registry / models / service 共用）。"""

# 角色类别
ROLE_CATEGORY_PLATFORM = "platform"
ROLE_CATEGORY_MODULE = "module"

# 角色类型（委派式权限管理）
# - system   系统管理员（super_admin，判定直接放行）
# - owner    模块负责人（内置，拥有该模块全部业务权限 + 模块管理入口）
# - delegate 模块代表（内置，权限集合与负责人一致，差异只在任命关系）
# - job      岗位角色 / 全局自定义角色（默认值，存量角色自动落入此类）
ROLE_TYPE_SYSTEM = "system"
ROLE_TYPE_OWNER = "owner"
ROLE_TYPE_DELEGATE = "delegate"
ROLE_TYPE_JOB = "job"

ROLE_TYPES: frozenset[str] = frozenset({ROLE_TYPE_SYSTEM, ROLE_TYPE_OWNER, ROLE_TYPE_DELEGATE, ROLE_TYPE_JOB})

# 已废弃的历史 role_type：`{module}:head`（XX负责人）/ `{module}:manager`（XX管理员），
# 2026-11-19 起由 owner / delegate 取代（见迁移 0203）。
# 仅用于「退役判据」与「列表过滤」，禁止作为可选 role_type 出现在注册表或新建入口。
RETIRED_ROLE_TYPES: frozenset[str] = frozenset({"head", "manager"})

# 受系统管理员独占管理的角色类型（只有模块负责人由系统管理员任命或移除；
# 模块代表由本模块负责人在模块配置页任命，见 delegation.can_assign_delegates）
ADMIN_ONLY_ROLE_TYPES: frozenset[str] = frozenset({ROLE_TYPE_SYSTEM, ROLE_TYPE_OWNER})

# 模块角色编码的保留字（角色编码第二段）
RESERVED_ROLE_NAMES: frozenset[str] = frozenset({ROLE_TYPE_OWNER, ROLE_TYPE_DELEGATE})

# 活跃系统管理员保底人数
MIN_ACTIVE_SUPERADMINS = 2

# 模块管理入口权限码约定：{module}:admin:read 中的 resource / action
ADMIN_ENTRY_RESOURCE = "admin"
ADMIN_ENTRY_ACTION = "read"


def admin_entry_code(module_code: str) -> str:
    return f"{module_code}:{ADMIN_ENTRY_RESOURCE}:{ADMIN_ENTRY_ACTION}"
