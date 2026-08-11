"""Dossier Writer request and response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ====== Product Dossier ======


class ProductDossierBase(BaseModel):
    product_name: str = Field(..., max_length=200, description="品种名称")
    sterile_type: str = Field(..., max_length=50, description="无菌/非无菌")
    manufacturer: str = Field(..., max_length=300, description="生产商")
    template_original_product_name: str | None = Field(None, max_length=200, description="模板原品种名称")
    template_original_manufacturer: str | None = Field(None, max_length=300, description="模板原生产商")


class ProductDossierCreate(ProductDossierBase):
    """创建品种资料请求"""

    pass


class ProductDossierUpdate(BaseModel):
    """更新品种资料请求"""

    product_name: str | None = Field(None, max_length=200)
    sterile_type: str | None = Field(None, max_length=50)
    manufacturer: str | None = Field(None, max_length=300)
    template_original_product_name: str | None = Field(None, max_length=200)
    template_original_manufacturer: str | None = Field(None, max_length=300)


class ProductDossierResponse(ProductDossierBase):
    """品种资料响应"""

    id: UUID
    status: str
    parse_status: str
    parse_error: str | None = None
    source_templates_path: str | None = None
    working_path: str | None = None
    assets_path: str | None = None
    outputs_path: str | None = None
    created_at: datetime
    updated_at: datetime
    chapter_count: int = 0

    class Config:
        from_attributes = True


class ProductDossierListResponse(BaseModel):
    """品种资料列表响应"""

    id: UUID
    product_name: str
    sterile_type: str
    manufacturer: str
    status: str
    parse_status: str
    chapter_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ====== Template ======


class TemplateResponse(BaseModel):
    """模板文件响应"""

    id: UUID
    original_filename: str
    file_size: int | None = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ====== Chapter ======


class ChapterResponse(BaseModel):
    """章节响应"""

    id: UUID
    parent_id: UUID | None = None
    chapter_code: str | None = None
    chapter_title: str
    level: int
    sort_order: int
    has_content: bool
    has_assets: bool
    asset_count: int = 0
    source_file: str | None = None
    working_file: str | None = None
    children: list["ChapterResponse"] = []

    class Config:
        from_attributes = True


class ChapterDetailResponse(BaseModel):
    """章节详情响应"""

    id: UUID
    product_dossier_id: UUID
    chapter_code: str | None = None
    chapter_title: str
    level: int
    has_content: bool
    has_assets: bool
    source_file: str | None = None
    working_file: str | None = None
    assets: list["AssetResponse"] = []

    class Config:
        from_attributes = True


# ====== Asset ======


class AssetResponse(BaseModel):
    """素材响应"""

    id: UUID
    original_filename: str
    file_type: str | None = None
    file_size: int | None = None
    uploaded_at: datetime
    category_id: UUID | None = None

    class Config:
        from_attributes = True


class AssetUploadResponse(BaseModel):
    """素材上传响应"""

    id: UUID
    original_filename: str
    file_path: str
    file_type: str | None = None
    file_size: int | None = None
    uploaded_at: datetime
    category_id: UUID | None = None


# ====== Parse Result ======


class ParseResultResponse(BaseModel):
    """解析结果响应"""

    success: bool
    message: str
    chapter_count: int = 0
    error: str | None = None


# ====== Export ======


class ExportRequest(BaseModel):
    """导出请求"""

    chapter_ids: list[UUID] | None = Field(None, description="指定章节ID列表，为空则导出全部")
    format: str = Field("docx", description="导出格式: docx/pdf")


class ExportResponse(BaseModel):
    """导出响应"""

    success: bool
    message: str
    file_path: str | None = None
    filename: str | None = None


# ====== AI Confirm ======

class AIConfirmRequest(BaseModel):
    """AI 填充确认请求"""
    fields: list[dict[str, Any]]

class AIFillResultItem(BaseModel):
    """AI 填充字段结果"""
    field_name: str
    status: str
    message: str

class AIConfirmData(BaseModel):
    """AI 填充确认响应数据"""
    success: bool
    message: str
    results: list[AIFillResultItem]

class AIConfirmResponse(BaseModel):
    """AI 填充确认响应"""
    code: int
    data: AIConfirmData
    message: str

# ====== Split Preview ======

class SplitPreviewRequest(BaseModel):
    """AI 拆分预览请求"""
    available_appendix_slots: list[str] = []

class PageSplitItem(BaseModel):
    """页拆分项"""
    page_number: int
    page_type: str
    content_summary: str
    appendix_slot: str | None = None

class SplitPreviewData(BaseModel):
    """AI 拆分预览响应数据"""
    success: bool
    message: str
    pages: list[PageSplitItem]
    page_count: int

class SplitPreviewResponse(BaseModel):
    """AI 拆分预览响应"""
    code: int
    data: SplitPreviewData
    message: str

# ====== Split Confirm ======

class SplitConfirmRequest(BaseModel):
    """AI 拆分确认请求"""
    splits: list[dict[str, Any]]

class SplitConfirmData(BaseModel):
    """AI 拆分确认响应数据"""
    success: bool
    message: str
    inserted_count: int

class SplitConfirmResponse(BaseModel):
    """AI 拆分确认响应"""
    code: int
    data: SplitConfirmData
    message: str

# ====== Asset Usage Toggle ======

class AssetUsageToggleRequest(BaseModel):
    """素材使用状态切换请求"""
    is_selected: bool

class AssetUsageToggleData(BaseModel):
    """素材使用状态切换响应数据"""
    usage_id: str | None = None
    is_selected: bool

class AssetUsageToggleResponse(BaseModel):
    """素材使用状态切换响应"""
    code: int
    data: AssetUsageToggleData
    message: str

# ====== Asset Category Update ======

class AssetCategoryUpdateRequest(BaseModel):
    """素材分类更新请求"""
    category_id: UUID | None = None

class AssetCategoryUpdateData(BaseModel):
    """素材分类更新响应数据"""
    id: str
    category_id: str | None

class AssetCategoryUpdateResponse(BaseModel):
    """素材分类更新响应"""
    code: int
    data: AssetCategoryUpdateData
    message: str


# 解决循环引用
ChapterResponse.model_rebuild()
ChapterDetailResponse.model_rebuild()
