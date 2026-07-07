"""质量检验试剂管理 Schema 定义

提供质量检验模块试剂/标准品管理的请求和响应数据模型。
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============ 请求模型 ============

class CreateReagentRequest(BaseModel):
    """创建试剂记录请求"""
    reagent_label_urls: list[str] = Field(default_factory=list, description="试剂标签图片URL数组")
    reagent_name: str = Field(..., description="试剂名称")
    arrival_date: date = Field(..., description="到货日期（默认当天）")
    production_date: Optional[date] = Field(None, description="生产日期（AI识别，默认到货日期+3年）")
    lot_no: str = Field(..., description="批号")
    incoming_lot_no: Optional[str] = Field(None, description="入场批号")
    expiration_date: date = Field(..., description="有效期")
    specification: Optional[str] = Field(None, description="规格")
    category: str = Field(..., description="分类（试剂/标准品）")
    reagent_no: Optional[str] = Field(None, description="编号")
    content: Optional[str] = Field(None, description="含量")
    manufacturer: Optional[str] = Field(None, description="生产厂家")
    unit: str = Field(..., description="单位")


class UpdateReagentRequest(BaseModel):
    """更新试剂记录请求"""
    reagent_label_urls: Optional[list[str]] = Field(None, description="试剂标签图片URL数组")
    reagent_name: Optional[str] = Field(None, description="试剂名称")
    arrival_date: Optional[date] = Field(None, description="到货日期")
    production_date: Optional[date] = Field(None, description="生产日期")
    lot_no: Optional[str] = Field(None, description="批号")
    incoming_lot_no: Optional[str] = Field(None, description="入场批号")
    expiration_date: Optional[date] = Field(None, description="有效期")
    specification: Optional[str] = Field(None, description="规格")
    category: Optional[str] = Field(None, description="分类")
    reagent_no: Optional[str] = Field(None, description="编号")
    content: Optional[str] = Field(None, description="含量")
    manufacturer: Optional[str] = Field(None, description="生产厂家")
    unit: Optional[str] = Field(None, description="单位")
    status: Optional[str] = Field(None, description="状态")


# ============ 响应模型 ============

class ReagentResponse(BaseModel):
    """试剂记录响应"""
    id: str
    reagent_label_urls: Optional[list[str]] = None
    reagent_name: str
    arrival_date: date
    production_date: Optional[date] = None
    lot_no: str
    incoming_lot_no: Optional[str] = None
    expiration_date: date
    specification: Optional[str] = None
    category: str
    reagent_no: Optional[str] = None
    content: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity: float
    unit: str
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

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
    reagent_name: Optional[str] = None
    lot_no: Optional[str] = None
    content: Optional[str] = None
    manufacturer: Optional[str] = None
    production_date: Optional[str] = None
    confidence: float = 0.0
    raw_response: Optional[str] = None


# ============ 查询参数 ============

class ReagentQueryParams(BaseModel):
    """试剂查询参数"""
    keyword: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 20