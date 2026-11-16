"""权限目录列表中文派生字段的单元测试。

目录页数据来自 DB（permission.permissions 镜像表），但「模块 / 资源 / 动作」三列要显示中文。
中文只能由后端从注册表派生：前端硬编码映射会与 registry 漂移，且新增模块时必然漏。
"""

from uuid import uuid4

from app.platform.permission.api import _permission_response
from app.platform.permission.models import Permission
from app.platform.permission.service.description import action_label


def _make(code: str, module: str, resource: str, action: str, name: str) -> Permission:
    return Permission(
        id=uuid4(),
        code=code,
        name=name,
        module=module,
        resource=resource,
        action=action,
        status="active",
        is_builtin=True,
    )


def test_registered_permission_gets_chinese_labels() -> None:
    permission = _make("quality:capa:read", "quality", "capa", "read", "查看CAPA")
    payload = _permission_response(permission)

    assert payload["module_label"] == "质量管理"
    assert payload["resource_label"] == "CAPA管理"
    assert payload["action_label"] == "查看"
    # 权限码本身是主键，必须原样保留
    assert payload["code"] == "quality:capa:read"


def test_retired_permission_code_falls_back_to_none() -> None:
    # registry 已退役但库里仍留着的码：中文列给 None，前端回退英文原值而不是显示空
    permission = _make("no:such:code", "no", "such", "code", "历史权限")
    payload = _permission_response(permission)

    assert payload["module_label"] is None
    assert payload["resource_label"] is None
    assert payload["action_label"] is None


def test_unknown_action_label_falls_back_to_raw_value() -> None:
    assert action_label("weird") == "weird"
