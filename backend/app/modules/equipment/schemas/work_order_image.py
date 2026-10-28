"""Work order image schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WorkOrderImageResponse(BaseModel):
    """工单图片响应"""

    id: uuid.UUID
    work_order_id: uuid.UUID
    file_name: str
    file_size: int | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class WorkOrderImageListApiResponse(BaseModel):
    """工单图片列表响应（声明具体响应体，避免 JSONResponse 绕过 response_model 校验）。"""

    code: int = 200
    message: str = "success"
    data: list[WorkOrderImageResponse] = Field(default_factory=list)


class WorkOrderImageDeleteApiResponse(BaseModel):
    """删除工单图片响应。"""

    code: int = 200
    message: str = "success"
    data: None = None
