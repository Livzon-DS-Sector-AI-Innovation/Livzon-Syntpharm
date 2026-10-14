"""权限模块对外公共 API。

其他模块 / Agent 工具复用同一套授权判定时，从这里导入，
不要直接 import permission 模块内部实现。
"""

from app.platform.permission.service.authorization import (
    PermissionContext,
    build_permission_context,
    has_permission,
)

__all__ = ["PermissionContext", "build_permission_context", "has_permission"]
