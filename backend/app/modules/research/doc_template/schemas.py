"""交付物模板的请求/响应模型（仅母本文件管理与版本留档）。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocGenTemplateFileData(BaseModel):
    """挂载 Word 模板原件后的回显信息。"""

    id: str
    file_name: str | None = None
    file_ext: str | None = None


class DocGenTemplateFileResponse(BaseModel):
    """POST /deliverable-templates/{id}/upload 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenTemplateFileData


class DocGenTemplateVersionItem(BaseModel):
    """模板的一个历史版本。"""

    id: UUID
    version_no: int
    file_name: str | None = None
    file_ext: str | None = None
    file_size: int | None = None
    template_code: str | None = None
    change_note: str | None = None
    is_current: bool = False
    created_by: UUID | None = None
    created_by_name: str | None = None
    created_at: datetime


class DocGenTemplateVersionListResponse(BaseModel):
    """GET /deliverable-templates/{id}/versions 响应。"""

    code: int = 200
    message: str = "success"
    data: list[DocGenTemplateVersionItem] = Field(default_factory=list)


class DocGenTemplateVersionRestoreData(BaseModel):
    """回滚结果：新生成的版本号及其来源版本。"""

    id: str
    template_id: str
    version_no: int
    from_version_no: int
    file_name: str | None = None
    file_ext: str | None = None


class DocGenTemplateVersionRestoreResponse(BaseModel):
    """POST /deliverable-templates/{id}/versions/{vid}/restore 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenTemplateVersionRestoreData


class DocGenOperationResponse(BaseModel):
    """仅回提示语的写操作响应（如删除历史版本）。"""

    code: int = 200
    message: str = "success"


class DocGenBatchUploadResult(BaseModel):
    """批量上传结果。

    同名文件不再计入 skipped，而是作为该模板的新版本计入 versioned。
    """

    created: list[dict[str, str | int]] = Field(default_factory=list)
    versioned: list[dict[str, str | int]] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)


class DocGenBatchUploadResponse(BaseModel):
    """POST /deliverable-templates/batch-upload 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenBatchUploadResult
