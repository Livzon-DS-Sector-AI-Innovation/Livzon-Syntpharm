"""系统管理 → 权限管理「模块负责人」入口的契约（2026-11-19 需求）。

- 全局入口只允许指派模块负责人（owner）；
- 模块代表（delegate）由模块负责人在模块配置页指派，全局入口必须拒绝。
"""

import uuid

import pytest
from pydantic import ValidationError

from app.platform.permission.schemas import ModuleAdminAssignRequest


def test_global_assign_accepts_owner() -> None:
    payload = ModuleAdminAssignRequest(module_code="quality", role_type="owner", user_id=uuid.uuid4())
    assert payload.role_type == "owner"


@pytest.mark.parametrize("role_type", ["delegate", "head", "manager", "job", ""])
def test_global_assign_rejects_non_owner(role_type: str) -> None:
    with pytest.raises(ValidationError):
        ModuleAdminAssignRequest(module_code="quality", role_type=role_type, user_id=uuid.uuid4())
