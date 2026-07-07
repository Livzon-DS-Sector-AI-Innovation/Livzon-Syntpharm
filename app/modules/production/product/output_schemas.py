"""Product output request and response schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ProductOutputCreate(BaseModel):
    """新建产量记录"""

    product_id: uuid.UUID = Field(..., description="产品ID")
    workshop: str = Field(..., max_length=64, description="车间名称")
    product_name: str = Field(..., max_length=255, description="产品名称")
    batch_no: str = Field(..., max_length=64, description="批号")
    production_date: date = Field(..., description="生产日期")
    end_date: date | None = Field(None, description="结束日期")
    weight: float = Field(..., ge=0, description="重量")
    unit: str = Field("kg", max_length=20, description="单位")
    notes: str | None = Field(None, description="备注")


class ProductOutputUpdate(BaseModel):
    """更新产量记录"""

    product_id: uuid.UUID | None = Field(None, description="产品ID")
    workshop: str | None = Field(None, max_length=64, description="车间名称")
    product_name: str | None = Field(None, max_length=255, description="产品名称")
    batch_no: str | None = Field(None, max_length=64, description="批号")
    production_date: date | None = Field(None, description="生产日期")
    end_date: date | None = Field(None, description="结束日期")
    weight: float | None = Field(None, ge=0, description="重量")
    unit: str | None = Field(None, max_length=20, description="单位")
    notes: str | None = Field(None, description="备注")


class ProductOutputResponse(BaseModel):
    """产量记录响应"""

    id: uuid.UUID
    product_id: uuid.UUID
    workshop: str
    product_name: str
    batch_no: str
    production_date: date
    end_date: date | None = None
    weight: float
    unit: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductOutputQueryParams(BaseModel):
    """查询参数"""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=200)
    workshop: str | None = Field(None, description="车间筛选")
    product_id: uuid.UUID | None = Field(None, description="产品筛选")
    product_name: str | None = Field(None, description="产品名称搜索")
    batch_no: str | None = Field(None, description="批号搜索")
    start_date: date | None = Field(None, description="起始日期")
    end_date: date | None = Field(None, description="结束日期")


class WorkshopSummary(BaseModel):
    """车间汇总"""

    workshop: str
    daily_total: float = Field(0, description="当日总重量")
    monthly_total: float = Field(0, description="当月总重量")
    yearly_total: float = Field(0, description="当年总重量")


class SummaryResponse(BaseModel):
    """汇总统计响应"""

    target_date: date | None = Field(None, description="查询日期")
    month: str | None = Field(None, description="查询月份 YYYY-MM")
    year: int | None = Field(None, description="查询年份")
    workshops: list[WorkshopSummary] = Field(default_factory=list)
    grand_total: float = Field(0, description="所有车间合计")
