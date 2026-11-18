from app.platform.identity.deps import (
    CurrentUser,
    OptionalUser,
    RequiredUser,
    get_current_user,
    require_current_user,
)
from app.platform.permission.deps import (
    PermissionContext,
    require_any_permission,
    require_assignment_admin,
    require_module_management,
    require_permission,
    require_role_catalog_read,
    require_route_permission,
)

__all__ = [
    "CurrentUser",
    "OptionalUser",
    "RequiredUser",
    "PermissionContext",
    "get_current_user",
    "require_current_user",
    "require_any_permission",
    "require_assignment_admin",
    "require_module_management",
    "require_permission",
    "require_role_catalog_read",
    "require_route_permission",
]
