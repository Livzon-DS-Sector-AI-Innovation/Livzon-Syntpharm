"""项目知识库的请求/响应模型。

约定与 doc_gen.schemas 一致：结构化响应的模型完整描述 code/message/data 实际返回体，
不使用 response_model=dict 或通用 ApiResponse。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KbDocumentItem(BaseModel):
    """知识库中的一份文档及其解析状态。"""

    id: UUID
    ragflow_document_id: str
    file_name: str
    file_ext: str = ""
    size_bytes: int = 0
    run: str = "UNSTART"
    progress: float = 0.0
    progress_msg: str = ""
    chunk_count: int = 0
    token_count: int = 0
    last_error: str = ""
    parse_started_at: datetime | None = None
    parsed_at: datetime | None = None
    created_at: datetime | None = None


class KnowledgeBaseItem(BaseModel):
    """知识库概要（列表与详情共用）。"""

    id: UUID
    project_id: UUID
    project_name: str = ""
    name: str
    description: str = ""
    provider: str = "ragflow"
    ragflow_dataset_id: str = ""
    embedding_model: str = ""
    chunk_method: str = "naive"
    status: str = "creating"
    last_error: str = ""
    document_count: int = 0
    chunk_count: int = 0
    token_count: int = 0
    parsed_count: int = 0
    parsing_count: int = 0
    failed_count: int = 0
    last_synced_at: datetime | None = None
    created_at: datetime | None = None


class KnowledgeBaseListResponse(BaseModel):
    """GET /research/knowledge-bases 响应。"""

    code: int = 200
    message: str = "success"
    data: list[KnowledgeBaseItem] = Field(default_factory=list)


class KnowledgeBaseDataResponse(BaseModel):
    """单条知识库响应（创建 / 详情 / 重试）。"""

    code: int = 200
    message: str = "success"
    data: KnowledgeBaseItem


class KbDocumentListResponse(BaseModel):
    """GET /research/knowledge-bases/{id}/documents 响应。"""

    code: int = 200
    message: str = "success"
    data: list[KbDocumentItem] = Field(default_factory=list)


class KbUploadSkipped(BaseModel):
    """被跳过的文件及原因（格式不支持 / 超限 / RAGFlow 拒绝）。"""

    file_name: str
    reason: str


class KbUploadResult(BaseModel):
    """上传结果：成功入队解析的文件、被跳过的文件与刷新后的文档列表。"""

    uploaded: list[str] = Field(default_factory=list)
    skipped: list[KbUploadSkipped] = Field(default_factory=list)
    documents: list[KbDocumentItem] = Field(default_factory=list)


class KbUploadResponse(BaseModel):
    """POST /research/knowledge-bases/{id}/documents 响应。"""

    code: int = 200
    message: str = "success"
    data: KbUploadResult


class KnowledgeBaseOperationResponse(BaseModel):
    """无数据体的操作响应（删除等）。"""

    code: int = 200
    message: str = "success"
    data: dict[str, str] = Field(default_factory=dict)


class KbChunkItem(BaseModel):
    """一条解析切片（预览「解析内容」用）。"""

    id: str = ""
    content: str = ""
    # 定位信息：RAGFlow 给的是 [[页序号, x0, x1, y0, y1], ...]，不解析只透传
    positions: list[list[float]] = Field(default_factory=list)
    document_keyword: str = ""
    image_id: str = ""
    available: bool = True


class KbChunkList(BaseModel):
    """切片分页结果。"""

    total: int = 0
    page: int = 1
    page_size: int = 50
    items: list[KbChunkItem] = Field(default_factory=list)


class KbChunkListResponse(BaseModel):
    """GET /research/knowledge-bases/{id}/documents/{doc_id}/chunks 响应。"""

    code: int = 200
    message: str = "success"
    data: KbChunkList = Field(default_factory=KbChunkList)


class KbLimits(BaseModel):
    """知识库上传限制（前端据此做提交前校验）。"""

    max_files: int = 10
    max_file_mb: int = 100
    allowed_extensions: list[str] = Field(default_factory=list)
    configured: bool = False
    provider: str = "ragflow"


class KbLimitsResponse(BaseModel):
    """上传前校验用的规模与格式限制。"""

    code: int = 200
    message: str = "success"
    data: KbLimits = Field(default_factory=KbLimits)


class KnowledgeBaseCreateRequest(BaseModel):
    """新建知识库请求：名称留空时由系统按项目名生成。"""

    project_id: UUID
    name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=1000)
    embedding_model: str = Field(default="", max_length=200)
    chunk_method: str = Field(default="", max_length=32)
