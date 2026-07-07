"""原料报告单 Pydantic Schemas"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============ ReportTemplate Schemas ============

class TemplateColumnConfig(BaseModel):
    """表格列配置"""
    key: str
    label: str
    type: str = "text"  # text, number, date, select
    width: Optional[int] = None
    required: bool = False
    options: Optional[list] = None  # 下拉选项


class TableFieldsConfig(BaseModel):
    """动态表格字段配置"""
    columns: list[TemplateColumnConfig] = []


class TemplateCreate(BaseModel):
    """模板创建"""
    template_name: str
    template_description: Optional[str] = None
    field_mapping: Optional[dict] = {}
    table_fields: Optional[dict] = {}


class TemplateUpdate(BaseModel):
    """模板更新"""
    template_name: Optional[str] = None
    template_description: Optional[str] = None
    field_mapping: Optional[dict] = None
    table_fields: Optional[dict] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    """模板响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_name: str
    template_file_url: str
    template_description: Optional[str] = None
    field_mapping: dict = {}
    table_fields: dict = {}
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None


class TemplateListItem(BaseModel):
    """模板列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_name: str
    template_description: Optional[str] = None
    is_active: bool = True
    created_at: datetime


# ============ MaterialReport Schemas ============

class ReportCreate(BaseModel):
    """报告单创建"""
    template_id: Optional[UUID] = None
    report_title: str
    report_date: date
    static_data: Optional[dict] = None


class ReportUpdate(BaseModel):
    """报告单更新"""
    template_id: Optional[UUID] = None
    report_title: Optional[str] = None
    report_date: Optional[date] = None
    static_data: Optional[dict] = None
    status: Optional[str] = None


class ReportItemData(BaseModel):
    """报告单明细数据"""
    row_index: int
    field_key: str
    field_value: Optional[str] = None


class ReportItemsBatchSave(BaseModel):
    """批量保存明细数据"""
    items: list[ReportItemData]


class ReportResponse(BaseModel):
    """报告单响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_no: str
    template_id: Optional[UUID] = None
    report_title: str
    report_date: date
    static_data: Optional[dict] = None
    status: str
    generated_file_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ReportListItem(BaseModel):
    """报告单列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_no: str
    template_id: Optional[UUID] = None
    template_name: Optional[str] = None
    report_title: str
    report_date: date
    status: str
    created_at: datetime


class ReportDetailResponse(BaseModel):
    """报告单详情响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_no: str
    template_id: Optional[UUID] = None
    template: Optional[TemplateResponse] = None
    report_title: str
    report_date: date
    static_data: Optional[dict] = None
    status: str
    generated_file_url: Optional[str] = None
    items: list = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class ReportFilter(BaseModel):
    """报告单筛选条件"""
    template_id: Optional[UUID] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    keyword: Optional[str] = None


# ============ Statistics Schemas ============

class ReportStatistics(BaseModel):
    """报告单统计"""
    total_count: int = 0
    draft_count: int = 0
    completed_count: int = 0
    approved_count: int = 0
    by_template: dict = {}