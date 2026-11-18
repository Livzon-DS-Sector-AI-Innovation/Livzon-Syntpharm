"""权限体系常量（无外部依赖，供 registry / models / service 共用）。"""

# 角色类别
ROLE_CATEGORY_PLATFORM = "platform"
ROLE_CATEGORY_MODULE = "module"

# 角色类型（委派式权限管理）
# - system  系统管理员（super_admin，判定直接放行）
# - head    模块负责人（内置，拥有该模块全部业务权限 + 模块管理入口）
# - manager 模块管理员（内置，只持有模块管理入口）
# - job     岗位角色 / 全局自定义角色（默认值，存量角色自动落入此类）
ROLE_TYPE_SYSTEM = "system"
ROLE_TYPE_HEAD = "head"
ROLE_TYPE_MANAGER = "manager"
ROLE_TYPE_JOB = "job"

ROLE_TYPES: frozenset[str] = frozenset({ROLE_TYPE_SYSTEM, ROLE_TYPE_HEAD, ROLE_TYPE_MANAGER, ROLE_TYPE_JOB})

# 受系统管理员独占管理的角色类型（模块负责人 / 模块管理员只能由系统管理员任命或移除）
ADMIN_ONLY_ROLE_TYPES: frozenset[str] = frozenset({ROLE_TYPE_SYSTEM, ROLE_TYPE_HEAD, ROLE_TYPE_MANAGER})

# 模块角色编码的保留字（角色编码第二段）
RESERVED_ROLE_NAMES: frozenset[str] = frozenset({"head", "manager"})

# 活跃系统管理员保底人数
MIN_ACTIVE_SUPERADMINS = 2

# 模块管理入口权限码约定：{module}:admin:read 中的 resource / action
ADMIN_ENTRY_RESOURCE = "admin"
ADMIN_ENTRY_ACTION = "read"


def admin_entry_code(module_code: str) -> str:
    return f"{module_code}:{ADMIN_ENTRY_RESOURCE}:{ADMIN_ENTRY_ACTION}"
