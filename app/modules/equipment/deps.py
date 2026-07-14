"""设备模块访问依赖。

提供 EquipmentAccessContext，供 API 端点、Service、Repository 统一使用。
所有登录用户拥有完整访问权限。
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends

from app.core.deps import require_current_user
from app.platform.identity.models import User


@dataclass
class EquipmentAccessContext:
    """设备模块访问上下文——包含用户信息。"""

    user: User
    data_scope: str = "all"
    department_user_ids: list[uuid.UUID] = field(default_factory=list)
    visible_department_ids: list[uuid.UUID] = field(default_factory=list)

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id

    @property
    def is_unrestricted(self) -> bool:
        return True


def require_equipment_access(*codes: str) -> Any:
    """依赖工厂：登录检查 + 构建访问上下文。

    用法:
        ctx: EquipmentAccessContext = Depends(
            require_equipment_access("equipment:asset:read")
        )
    """

    async def _dependency(
        user: User = Depends(require_current_user),
    ) -> EquipmentAccessContext:
        return EquipmentAccessContext(user=user)

    return _dependency
