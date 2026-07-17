"""质量检验试剂管理 Schema 定义

提供质量检验模块试剂/标准品管理的请求和响应数据模型。
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

# ============ 请求模型 ============


class CreateReagentRequest(BaseModel):
    """创建试剂记录请求"""

    reagent_label_urls: list[str] = Field(default_factory=list, description="试剂标签图片URL数组")
    reagent_name: str = Field(..., description="试剂名称")
    arrival_date: date = Field(..., description="到货日期（默认当天）")
    production_date: date | None = Field(None, description="生产日期（AI识别，默认到货日期+3年）")
    lot_no: str = Field(..., description="批号")
    incoming_lot_no: str | None = Field(None, description="入场批号")
    expiration_date: date = Field(..., description="有效期")
    specification: str | None = Field(None, description="规格")
    category: str = Field(..., description="分类（试剂/标准品）")
    reagent_no: str | None = Field(None, description="编号")
    content: str | None = Field(None, description="含量")
    manufacturer: str | None = Field(None, description="生产厂家")
    unit: str = Field(..., description="单位")


class UpdateReagentRequest(BaseModel):
    """更新试剂记录请求"""

    reagent_label_urls: list[str] | None = Field(None, description="试剂标签图片URL数组")
    reagent_name: str | None = Field(None, description="试剂名称")
    arrival_date: date | None = Field(None, description="到货日期")
    production_date: date | None = Field(None, description="生产日期")
    lot_no: str | None = Field(None, description="批号")
    incoming_lot_no: str | None = Field(None, description="入场批号")
    expiration_date: date | None = Field(None, description="有效期")
    specification: str | None = Field(None, description="规格")
    category: str | None = Field(None, description="分类")
    reagent_no: str | None = Field(None, description="编号")
    content: str | None = Field(None, description="含量")
    manufacturer: str | None = Field(None, description="生产厂家")
    unit: str | None = Field(None, description="单位")
    status: str | None = Field(None, description="状态")


# ============ 响应模型 ============


class ReagentResponse(BaseModel):
    """试剂记录响应"""

    id: str
    reagent_label_urls: list[str] | None = None
    reagent_name: str
    arrival_date: date
    production_date: date | None = None
    lot_no: str
    incoming_lot_no: str | None = None
    expiration_date: date
    specification: str | None = None
    category: str
    reagent_no: str | None = None
    content: str | None = None
    manufacturer: str | None = None
    quantity: float
    unit: str
    status: str
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ReagentListResponse(BaseModel):
    """试剂列表响应"""

    items: list[ReagentResponse]
    total: int
    page: int
    page_size: int


class AiRecognizeResponse(BaseModel):
    """AI识别试剂标签响应"""

    reagent_name: str | None = None
    lot_no: str | None = None
    content: str | None = None
    manufacturer: str | None = None
    production_date: str | None = None
    confidence: float = 0.0
    raw_response: str | None = None


# ============ 查询参数 ============


class ReagentQueryParams(BaseModel):
    """试剂查询参数"""

    keyword: str | None = None
    category: str | None = None
    status: str | None = None
    page: int = 1
    page_size: int = 20
