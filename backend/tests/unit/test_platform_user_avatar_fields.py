# mypy: ignore-errors
"""操作记录 / 授权列表的用户展示字段契约。

前端在「操作者」「授权用户」列左侧渲染飞书头像，依赖响应里带 `avatar_url`
（小图优先）与 `username`；这里锁住字段，避免后续重构把展示字段删掉。
"""

import uuid
from datetime import UTC, datetime

from app.platform.audit.schemas import AuditLogItem
from app.platform.permission.schemas import GrantResponse


def test_audit_log_item_exposes_avatar() -> None:
    item = AuditLogItem(
        id=uuid.uuid4(),
        action="user.update",
        created_at=datetime.now(UTC),
        user_name="张三",
        username="liujg",
        avatar_url="https://cdn.example.com/a_t.png",
    )

    payload = item.model_dump()
    assert payload["avatar_url"] == "https://cdn.example.com/a_t.png"
    assert payload["user_name"] == "张三"
    assert payload["username"] == "liujg"


def test_audit_log_item_avatar_optional() -> None:
    item = AuditLogItem(id=uuid.uuid4(), action="system.cleanup", created_at=datetime.now(UTC))

    assert item.avatar_url is None


def test_grant_response_exposes_user_identity_fields() -> None:
    grant = GrantResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role_id=uuid.uuid4(),
        scope_type="all",
        user_name="张三",
        username="liujg",
        avatar_url="https://cdn.example.com/a_t.png",
    )

    payload = grant.model_dump()
    assert payload["username"] == "liujg"
    assert payload["avatar_url"] == "https://cdn.example.com/a_t.png"
