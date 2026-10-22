"""操作记录响应 schema。"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogItem(BaseModel):
    """单条操作记录（含操作者姓名/账号，join identity.users）。"""

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    user_name: str | None = None
    username: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    extra: dict[str, Any] | None = None
    ip_address: str | None = None
    created_at: datetime


class AuditLogListData(BaseModel):
    """操作记录分页数据（与登录记录返回结构保持一致：items / total / page / page_size）。"""

    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


class AuditLogListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AuditLogListData
