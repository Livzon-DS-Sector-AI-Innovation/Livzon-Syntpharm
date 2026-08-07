"""Product output request and response schemas."""

import uuid
from datetime import date, datetime
from typing import Any

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
    page_size: int = Field(20, ge=1, le=5000)
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


class MonthlyTrend(BaseModel):
    """月度趋势数据"""

    month: int = Field(..., description="月份 1-12")
    current_year_weight: float = Field(0, description="当年产量(kg)")
    previous_year_weight: float = Field(0, description="去年产量(kg)")


class WorkshopRanking(BaseModel):
    """车间排名"""

    workshop: str = Field(..., description="车间名称")
    total_weight: float = Field(0, description="年度总产量(kg)")
    batch_count: int = Field(0, description="批次数")


class TopProduct(BaseModel):
    """TOP产品"""

    rank: int = Field(..., description="排名")
    product_name: str = Field(..., description="产品名称")
    workshop: str = Field(..., description="车间")
    total_weight: float = Field(0, description="年度总产量(kg)")
    batch_count: int = Field(0, description="批次数")
    avg_weight: float = Field(0, description="平均批次重量(kg)")


class AnnualOverview(BaseModel):
    """年度概览"""

    total_weight: float = Field(0, description="年度总产量(kg)")
    previous_year_weight: float = Field(0, description="去年总产量(kg)")
    weight_yoy: float = Field(0, description="产量同比(%)")
    total_batches: int = Field(0, description="年度总批次")
    previous_year_batches: int = Field(0, description="去年总批次")
    batch_yoy: float = Field(0, description="批次同比(%)")
    active_workshops: int = Field(0, description="活跃车间数")
    active_products: int = Field(0, description="活跃产品数")


class AnnualReviewResponse(BaseModel):
    """年度回顾响应"""

    year: int = Field(..., description="年份")
    overview: AnnualOverview = Field(default_factory=AnnualOverview)
    monthly_trend: list[MonthlyTrend] = Field(default_factory=list)
    workshop_ranking: list[WorkshopRanking] = Field(default_factory=list)
    top_products: list[TopProduct] = Field(default_factory=list)


class PreviewPushResponse(BaseModel):
    """预览推送响应"""

    to_create: list[dict[str, Any]] = Field(default_factory=list, description="待新增记录")
    to_update: list[dict[str, Any]] = Field(default_factory=list, description="待更新记录")
    to_skip: list[dict[str, Any]] = Field(default_factory=list, description="待跳过记录")


class PreviewPullResponse(BaseModel):
    """预览拉取响应"""

    to_create: list[dict[str, Any]] = Field(default_factory=list, description="待新增记录")
    to_update: list[dict[str, Any]] = Field(default_factory=list, description="待更新记录")


class UndoSyncResponse(BaseModel):
    """撤销同步响应"""

    deleted: int = Field(..., description="删除的记录数")


class PreviewImportResponse(BaseModel):
    """预览导入响应"""

    total_rows: int = Field(..., description="总行数")
    valid_records: int = Field(..., description="有效记录数")
    invalid_records: int = Field(..., description="无效记录数")
    new_records: int = Field(..., description="新增记录数")
    duplicate_records: int = Field(..., description="重复记录数")
    not_found_product: int = Field(..., description="未找到产品的记录数")
    records: list[dict[str, Any]] = Field(default_factory=list, description="记录详情")
    invalid_details: list[dict[str, Any]] = Field(default_factory=list, description="无效记录详情")


class UndoImportResponse(BaseModel):
    """撤销导入响应"""

    deleted: int = Field(..., description="删除的记录数")
    batch_id: str = Field(..., description="批次 ID")


class ImportResponse(BaseModel):
    """导入响应"""

    imported: int = Field(..., description="导入记录数")
    skipped: int = Field(..., description="跳过记录数")
    batch_id: str = Field(..., description="批次 ID")
