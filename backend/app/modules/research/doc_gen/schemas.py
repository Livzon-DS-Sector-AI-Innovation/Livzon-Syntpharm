"""文档生成模块的请求/响应模型。

约定：所有结构化响应的模型都完整描述 code/message/data 实际返回体，
不使用 response_model=dict 或通用 ApiResponse。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

FileRole = Literal["material", "literature", "report_draft", "supplement"]


class DocGenTemplateSummary(BaseModel):
    """模板摘要（供前端下拉选择）。"""

    code: str
    name: str
    version: str
    stage: str = ""
    description: str = ""
    slot_count: int = 0
    required_count: int = 0
    unfilled_notes: list[str] = Field(default_factory=list)


class DocGenSupportedFormat(BaseModel):
    """一种受支持的资料类型：扩展名 + 实际使用的提取库。

    由解析层的类型注册表派生（唯一真相来源），前端提示与运维核对都读它。
    """

    name: str
    extensions: list[str] = Field(default_factory=list)
    library: str
    needs_ocr: bool = False


class DocGenLimits(BaseModel):
    """上传与任务规模限制（前端据此做提交前校验）。"""

    max_files: int = 20
    max_total_pages: int = 150
    max_file_mb: int = 30
    max_total_mb: int = 150
    allowed_extensions: list[str] = Field(default_factory=list)
    supported_formats: list[DocGenSupportedFormat] = Field(default_factory=list)


class DocGenSlotProfile(BaseModel):
    """内置填充项配置（上传 Word 模板时选择用）。"""

    code: str
    name: str
    version: str
    stage: str = ""
    description: str = ""
    slot_count: int = 0
    required_count: int = 0
    unfilled_notes: list[str] = Field(default_factory=list)


class DocGenSlotProfileListResponse(BaseModel):
    """GET /doc-gen/slot-profiles 响应。"""

    code: int = 200
    message: str = "success"
    data: list[DocGenSlotProfile] = Field(default_factory=list)


class DocGenUsableTemplate(BaseModel):
    """可用于 AI 生成的交付物模板（必须有 Word 模板原件 + 合法填充项配置）。"""

    id: UUID
    name: str
    template_code: str
    template_version: str
    stage: str
    description: str = ""
    file_name: str | None = None
    file_ext: str | None = None
    slot_count: int = 0
    required_count: int = 0
    unfilled_notes: list[str] = Field(default_factory=list)


class DocGenUsableTemplateListResponse(BaseModel):
    """GET /doc-gen/templates 响应。"""

    code: int = 200
    message: str = "success"
    data: list[DocGenUsableTemplate] = Field(default_factory=list)


class DocGenTemplateListResponse(BaseModel):
    """GET /doc-gen/builtin-templates 响应（内置模板，排错用）。"""

    code: int = 200
    message: str = "success"
    data: list[DocGenTemplateSummary] = Field(default_factory=list)


class DocGenTemplateFileData(BaseModel):
    """挂载 Word 模板原件后的回显信息。"""

    id: str
    file_name: str | None = None
    file_ext: str | None = None


class DocGenTemplateFileResponse(BaseModel):
    """POST /doc-gen/deliverable-templates/{id}/upload 响应。"""

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
    """GET /doc-gen/deliverable-templates/{id}/versions 响应。"""

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
    """POST /doc-gen/deliverable-templates/{id}/versions/{vid}/restore 响应。"""

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

    created: list[dict[str, str]] = Field(default_factory=list)
    versioned: list[dict[str, str]] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)


class DocGenBatchUploadResponse(BaseModel):
    """POST /doc-gen/deliverable-templates/batch-upload 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenBatchUploadResult


class DocGenLimitsResponse(BaseModel):
    """GET /doc-gen/limits 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenLimits


class DocGenInputFileResponse(BaseModel):
    """资料文件条目。"""

    id: UUID
    original_filename: str
    role: FileRole
    size_bytes: int
    page_count: int = 0
    char_count: int = 0
    parse_status: str
    warnings: list[str] | None = None
    model_config = {"from_attributes": True}


class DocGenSlotValueResponse(BaseModel):
    """填充项结果条目。"""

    id: UUID
    slot_key: str
    label: str
    text: str | None = None
    rows: list[Any] | None = None
    state: str
    reason: str | None = None
    confidence: float | None = None
    evidence: list[Any] | None = None
    candidates: list[Any] | None = None
    section_key: str | None = None
    instance_index: int | None = None
    pre_compose_text: str | None = None  # 成文前的人工确认文本（成文改写后可对照）
    model_config = {"from_attributes": True}


class DocGenSectionResponse(BaseModel):
    """大纲中的一个章节实例。"""

    id: UUID
    section_key: str
    fragment_key: str
    extension_point_key: str
    parent_section_key: str | None = None
    level: int
    title: str
    order_index: int
    source: str
    state: str
    trigger_trace: dict[str, Any] | None = None
    title_pool: list[str] = Field(default_factory=list)  # 供前端换标题的下拉（由模板规格补充）
    model_config = {"from_attributes": True}


class DocGenJobResponse(BaseModel):
    """任务状态（列表与轮询共用）。"""

    id: UUID
    report_id: UUID | None = None
    project_id: UUID | None = None
    template_code: str
    template_version: str
    status: str
    step: str
    progress: int
    has_document: bool = False
    has_report: bool = False
    error_code: str | None = None
    error_message: str | None = None
    stats: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    parent_job_id: UUID | None = None
    supplement_text: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
    model_config = {"from_attributes": True}


class DocGenJobDetail(BaseModel):
    """任务详情（含资料、填充项结果与大纲）。"""

    job: DocGenJobResponse
    files: list[DocGenInputFileResponse] = Field(default_factory=list)
    slots: list[DocGenSlotValueResponse] = Field(default_factory=list)
    sections: list[DocGenSectionResponse] = Field(default_factory=list)


class DocGenJobDataResponse(BaseModel):
    """POST /jobs、POST /jobs/{id}/cancel 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenJobResponse


class DocGenJobDetailResponse(BaseModel):
    """GET /jobs/{id} 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenJobDetail


class DocGenExtractedInfoResponse(BaseModel):
    """GET /jobs/{id}/extracted-info 响应。"""

    code: int = 200
    message: str = "success"
    data: dict[str, list[DocGenSlotValueResponse]]


class DocGenSectionAdjust(BaseModel):
    """人工对大纲中一个章节的调整（确认时随填充项一并提交）。"""

    section_key: str
    state: Literal["enabled", "disabled"] | None = None
    title: str | None = None  # 必须是该片段预设标题池中的一项
    order_index: int | None = None


class DocGenConfirmRequest(BaseModel):
    """POST /jobs/{id}/confirm 请求体：人工改过的填充项 + 大纲调整。"""

    slots: dict[str, str] = Field(default_factory=dict, description="填充项 key → 人工修正后的文本")
    outline: list[DocGenSectionAdjust] = Field(default_factory=list, description="大纲调整（启用/禁用/换标题/排序）")


class DocGenJobUpdateRequest(BaseModel):
    """PATCH /jobs/{id} 请求体：修改基本信息与补充说明（仅草稿/复核/失败状态可改）。"""

    doc_code: str | None = Field(None, description="受控编码")
    doc_version: str | None = Field(None, description="版本号")
    drug_name: str | None = Field(None, description="品种名称")
    supplement_text: str | None = Field(None, description="补充说明（重新生成时自动沿用）")
    template_code: str | None = Field(None, description="模板ID（变更模板）")


class DocGenSupersededItem(BaseModel):
    """已失效的上轮生成任务（重新生成链上的历史节点）。"""

    id: UUID
    status: str
    step: str
    progress: int
    created_at: datetime
    finished_at: datetime | None = None


class DocGenSupersededList(BaseModel):
    """失效任务清单。"""

    items: list[DocGenSupersededItem] = Field(default_factory=list)
    total: int = 0


class DocGenSupersededResponse(BaseModel):
    """GET /jobs/{id}/superseded 响应。"""

    code: int = 200
    message: str = "success"
    data: DocGenSupersededList


class DocGenOutlineResponse(BaseModel):
    """GET /jobs/{id}/outline 响应。"""

    code: int = 200
    message: str = "success"
    data: list[DocGenSectionResponse] = Field(default_factory=list)


class DocGenJobListResponse(BaseModel):
    """GET /jobs?report_id= 响应。"""

    code: int = 200
    message: str = "success"
    data: list[DocGenJobResponse] = Field(default_factory=list)


class DocGenMessageResponse(BaseModel):
    """会话消息条目。"""

    id: UUID
    role: str
    content: str
    slot_updates: list[Any] | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class DocGenConversationResponse(BaseModel):
    """任务对话会话状态。"""

    id: UUID
    job_id: UUID
    status: str
    round_count: int
    max_rounds: int
    created_at: datetime
    model_config = {"from_attributes": True}


class DocGenConversationData(BaseModel):
    """会话 + 消息列表（GET conversation 与 POST messages 共用）。"""

    conversation: DocGenConversationResponse
    messages: list[DocGenMessageResponse] = Field(default_factory=list)


class DocGenConversationDataResponse(BaseModel):
    """对话数据响应（信封格式）。"""

    code: int = 200
    message: str = "success"
    data: DocGenConversationData | None = None


class DocGenSendMessageRequest(BaseModel):
    """POST /jobs/{id}/messages 请求体。"""

    content: str = Field(min_length=1, max_length=4000, description="用户消息内容")


class DocGenSendMessageResponse(BaseModel):
    """发送消息响应：返回会话状态与全部消息（含刚写入的用户消息与助手回复）。"""

    code: int = 200
    message: str = "success"
    data: DocGenConversationData | None = None


__all__ = [
    "DocGenBatchUploadResponse",
    "DocGenBatchUploadResult",
    "DocGenConfirmRequest",
    "DocGenConversationData",
    "DocGenConversationDataResponse",
    "DocGenConversationResponse",
    "DocGenExtractedInfoResponse",
    "DocGenInputFileResponse",
    "DocGenJobDataResponse",
    "DocGenJobDetail",
    "DocGenJobDetailResponse",
    "DocGenJobListResponse",
    "DocGenJobResponse",
    "DocGenJobUpdateRequest",
    "DocGenLimits",
    "DocGenLimitsResponse",
    "DocGenMessageResponse",
    "DocGenOutlineResponse",
    "DocGenSectionAdjust",
    "DocGenSectionResponse",
    "DocGenSendMessageRequest",
    "DocGenSendMessageResponse",
    "DocGenSlotProfile",
    "DocGenTemplateFileData",
    "DocGenTemplateFileResponse",
    "DocGenSlotProfileListResponse",
    "DocGenSlotValueResponse",
    "DocGenSupersededItem",
    "DocGenSupersededList",
    "DocGenSupersededResponse",
    "DocGenTemplateListResponse",
    "DocGenTemplateSummary",
    "DocGenUsableTemplate",
    "DocGenUsableTemplateListResponse",
]
