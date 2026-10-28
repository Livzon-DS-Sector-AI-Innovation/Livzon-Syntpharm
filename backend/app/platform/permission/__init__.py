"""权限体系平台能力（permission schema）。"""

from app.platform.permission.models import (
    ApiBinding,
    Permission,
    Role,
    RolePermission,
    UserRoleGrant,
)

__all__ = ["ApiBinding", "Permission", "Role", "RolePermission", "UserRoleGrant"]
