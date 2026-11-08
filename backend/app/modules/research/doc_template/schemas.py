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


# ---------------------------------------------------------------------------
# 槽位结构（人工可编辑的 JSON 文档，不落表）
# ---------------------------------------------------------------------------


class DocGenSlotAnchorData(BaseModel):
    """母本里的一个具体位置（段落或表格单元格）。"""

    kind: str = ""
    index: int | None = None
    table_index: int | None = None
    row: int | None = None
    col: int | None = None
    para_index: int | None = None
    text: str = ""
    style: str = ""
    fingerprint: str = ""


class DocGenSlotItem(BaseModel):
    """一个可填槽位；``candidate_id`` 与 ``anchor`` 二选一即可换绑位置。"""

    slot_key: str = Field(..., max_length=100)
    label: str = Field(..., max_length=200)
    value_type: str = Field("text", max_length=20)
    owner_hint: str | None = Field(None, max_length=100)
    hint: str | None = Field(None, max_length=300)
    location: str | None = Field(None, max_length=200)
    candidate_id: str | None = Field(None, max_length=80)
    anchor: DocGenSlotAnchorData | None = None
    is_enabled: bool = True
    origin: str = Field("ai", max_length=20)
    edited_fields: list[str] = Field(default_factory=list)


class DocGenSlotCandidateItem(BaseModel):
    """母本里的候选位置；``used`` 表示已被某个槽位占用。"""

    candidate_id: str
    kind: str
    label: str
    text: str = ""
    style: str = ""
    context: str = ""
    used: bool = False


class DocGenTemplateSlotsData(BaseModel):
    """GET /deliverable-templates/{id}/slots 响应体。"""

    template_id: str
    template_name: str
    file_name: str | None = None
    version: int = 2
    source_key: str | None = None
    analyzed_at: str | None = None
    edited_at: str | None = None
    token: str | None = None
    is_stale: bool = False
    slots: list[DocGenSlotItem] = Field(default_factory=list)
    candidates: list[DocGenSlotCandidateItem] = Field(default_factory=list)
    candidate_total: int = 0
    total_count: int = 0
    enabled_count: int = 0


class DocGenTemplateSlotsResponse(BaseModel):
    """GET /deliverable-templates/{id}/slots 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenTemplateSlotsData


class DocGenTemplateSlotsSaveRequest(BaseModel):
    """PUT /deliverable-templates/{id}/slots 入参：全量覆盖 + 乐观令牌。"""

    slots: list[DocGenSlotItem] = Field(..., min_length=1)
    token: str | None = Field(None, max_length=64)


class DocGenReparseStats(BaseModel):
    """合并重解析的增减统计。"""

    added: int = 0
    kept: int = 0
    removed: int = 0


class DocGenTemplateSlotsSaveData(BaseModel):
    """保存/重解析后的回显。"""

    slots: list[DocGenSlotItem] = Field(default_factory=list)
    token: str | None = None
    analyzed_at: str | None = None
    edited_at: str | None = None
    total_count: int = 0
    enabled_count: int = 0


class DocGenTemplateSlotsSaveResponse(BaseModel):
    """PUT /deliverable-templates/{id}/slots 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenTemplateSlotsSaveData


class DocGenTemplateSlotsReparseRequest(BaseModel):
    """POST /deliverable-templates/{id}/slots/reparse 入参。"""

    token: str | None = Field(None, max_length=64)


class DocGenTemplateSlotsReparseData(DocGenTemplateSlotsSaveData):
    """重解析结果：AI 本次原始识别 + 合并后结果 + 统计（diff 只在响应里，不落库）。"""

    ai_slots: list[DocGenSlotItem] = Field(default_factory=list)
    stats: DocGenReparseStats = Field(default_factory=DocGenReparseStats)


class DocGenTemplateSlotsReparseResponse(BaseModel):
    """POST /deliverable-templates/{id}/slots/reparse 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenTemplateSlotsReparseData
