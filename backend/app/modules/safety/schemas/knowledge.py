"""Safety request and response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.safety.schemas.enums import (
    KnowledgeCategory,
)


class SafetyKnowledgeArticleBase(BaseModel):
    """安全知识库文章基础模式"""

    title: str = Field(..., max_length=255, description="文章标题")
    summary: str | None = Field(None, description="摘要")
    content: str | None = Field(None, description="正文内容")
    tags: str | None = Field(None, max_length=500, description="标签（逗号分隔）")
    category: KnowledgeCategory = Field(KnowledgeCategory.OTHER, description="分类")


class SafetyKnowledgeArticleCreate(SafetyKnowledgeArticleBase):
    """创建知识库文章"""

    article_no: str | None = Field(None, max_length=64, description="文档编号")
    source: str | None = Field(None, max_length=255, description="来源")
    author: str | None = Field(None, max_length=255, description="作者")
    publish_date: datetime | None = Field(None, description="发布日期")
    notes: str | None = Field(None, description="备注")


class SafetyKnowledgeArticleUpdate(BaseModel):
    """更新知识库文章"""

    title: str | None = Field(None, max_length=255, description="文章标题")
    summary: str | None = Field(None, description="摘要")
    content: str | None = Field(None, description="正文内容")
    tags: str | None = Field(None, max_length=500, description="标签（逗号分隔）")
    category: KnowledgeCategory | None = Field(None, description="分类")
    status: str | None = Field(None, max_length=32, description="状态")
    article_no: str | None = Field(None, max_length=64, description="文档编号")
    source: str | None = Field(None, max_length=255, description="来源")
    author: str | None = Field(None, max_length=255, description="作者")
    publish_date: datetime | None = Field(None, description="发布日期")
    notes: str | None = Field(None, description="备注")


class SafetyKnowledgeArticleResponse(SafetyKnowledgeArticleBase):
    """安全知识库文章响应"""

    id: uuid.UUID
    status: str
    view_count: int = 0
    attachment_path: str | None = None
    attachment_original_name: str | None = None
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    # ── 文档管控字段 ──
    article_no: str | None = None
    version: int = 1
    source: str | None = None
    author: str | None = None
    publish_date: datetime | None = None
    superseded_by_id: uuid.UUID | None = None
    superseded_by_title: str | None = None
    notes: str | None = None

    class Config:
        from_attributes = True


# ============ API Response Wrappers ============


class SafetyKnowledgeArticleApiResponse(BaseModel):
    """Single safety knowledge article response wrapper"""

    code: int = 200
    message: str = "success"
    data: SafetyKnowledgeArticleResponse | None = None


class SafetyKnowledgeArticleListApiResponse(BaseModel):
    """Safety knowledge article list response wrapper"""

    code: int = 200
    message: str = "success"
    data: list[SafetyKnowledgeArticleResponse]
    meta: dict[str, Any] | None = None


# ============ Non-article knowledge endpoint response models ============


class SafetyKnowledgeGeneratedCardContent(BaseModel):
    """AI 生成的知识卡片内容（LLM 自由字段，允许额外键）"""

    model_config = ConfigDict(extra="allow")

    title: Any = None
    key_points: Any = None
    applicable_scope: Any = None
    important_deadlines: Any = None
    responsible_parties: Any = None
    penalties: Any = None
    summary: Any = None
    message: Any = None


class SafetyKnowledgeGenerateCardApiResponse(BaseModel):
    """生成知识卡片响应包装"""

    code: int = 200
    message: str = "success"
    data: SafetyKnowledgeGeneratedCardContent | None = None


class SafetyKnowledgePptData(BaseModel):
    """AI 生成 PPT 的数据体"""

    download_url: str
    file_name: str
    page_count: int
    message: str


class SafetyKnowledgeGeneratePptApiResponse(BaseModel):
    """生成 PPT 响应包装"""

    code: int = 200
    message: str = "success"
    data: SafetyKnowledgePptData | None = None


class SafetyKnowledgePptRecordItem(BaseModel):
    """PPT 生成历史记录项"""

    id: str
    file_name: str
    template: str
    style: str
    page_count: int
    download_url: str
    created_at: str | None = None


class SafetyKnowledgePptHistoryData(BaseModel):
    """PPT 生成历史数据体"""

    records: list[SafetyKnowledgePptRecordItem]
    total: int


class SafetyKnowledgePptHistoryApiResponse(BaseModel):
    """PPT 生成历史响应包装"""

    code: int = 200
    message: str = "success"
    data: SafetyKnowledgePptHistoryData


class SafetyKnowledgeSummaryData(BaseModel):
    """AI 生成摘要数据体"""

    summary: str
    message: str


class SafetyKnowledgeGenerateSummaryApiResponse(BaseModel):
    """生成摘要响应包装"""

    code: int = 200
    message: str = "success"
    data: SafetyKnowledgeSummaryData | None = None


class SafetyKnowledgeBatchImportResultItem(BaseModel):
    """批量导入单文件结果"""

    filename: str
    status: str
    message: str | None = None
    article_id: str | None = None
    title: str | None = None
    category: str | None = None


class SafetyKnowledgeBatchImportSummary(BaseModel):
    """批量导入汇总"""

    total: int
    success: int
    error: int


class SafetyKnowledgeBatchImportData(BaseModel):
    """批量导入数据体"""

    results: list[SafetyKnowledgeBatchImportResultItem]
    summary: SafetyKnowledgeBatchImportSummary


class SafetyKnowledgeBatchImportApiResponse(BaseModel):
    """批量导入响应包装"""

    code: int = 200
    message: str = "success"
    data: SafetyKnowledgeBatchImportData | None = None
