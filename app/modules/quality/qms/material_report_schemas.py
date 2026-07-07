"""原料报告单 Pydantic Schemas"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ============ ReportTemplate Schemas ============


class TemplateColumnConfig(BaseModel):
    """表格列配置"""

    key: str
    label: str
    type: str = "text"  # text, number, date, select
    width: int | None = None
    required: bool = False
    options: list | None = None  # 下拉选项


class TableFieldsConfig(BaseModel):
    """动态表格字段配置"""

    columns: list[TemplateColumnConfig] = []


class TemplateCreate(BaseModel):
    """模板创建"""

    template_name: str
    template_description: str | None = None
    field_mapping: dict | None = {}
    table_fields: dict | None = {}


class TemplateUpdate(BaseModel):
    """模板更新"""

    template_name: str | None = None
    template_description: str | None = None
    field_mapping: dict | None = None
    table_fields: dict | None = None
    is_active: bool | None = None


class TemplateResponse(BaseModel):
    """模板响应"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_name: str
    template_file_url: str
    template_description: str | None = None
    field_mapping: dict = {}
    table_fields: dict = {}
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None = None


class TemplateListItem(BaseModel):
    """模板列表项"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_name: str
    template_description: str | None = None
    is_active: bool = True
    created_at: datetime


# ============ MaterialReport Schemas ============


class ReportCreate(BaseModel):
    """报告单创建"""

    template_id: UUID | None = None
    report_title: str
    report_date: date
    static_data: dict | None = None


class ReportUpdate(BaseModel):
    """报告单更新"""

    template_id: UUID | None = None
    report_title: str | None = None
    report_date: date | None = None
    static_data: dict | None = None
    status: str | None = None


class ReportItemData(BaseModel):
    """报告单明细数据"""

    row_index: int
    field_key: str
    field_value: str | None = None


class ReportItemsBatchSave(BaseModel):
    """批量保存明细数据"""

    items: list[ReportItemData]


class ReportResponse(BaseModel):
    """报告单响应"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_no: str
    template_id: UUID | None = None
    report_title: str
    report_date: date
    static_data: dict | None = None
    status: str
    generated_file_url: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ReportListItem(BaseModel):
    """报告单列表项"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_no: str
    template_id: UUID | None = None
    template_name: str | None = None
    report_title: str
    report_date: date
    status: str
    created_at: datetime


class ReportDetailResponse(BaseModel):
    """报告单详情响应"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_no: str
    template_id: UUID | None = None
    template: TemplateResponse | None = None
    report_title: str
    report_date: date
    static_data: dict | None = None
    status: str
    generated_file_url: str | None = None
    items: list = []
    created_at: datetime
    updated_at: datetime | None = None


class ReportFilter(BaseModel):
    """报告单筛选条件"""

    template_id: UUID | None = None
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    keyword: str | None = None


# ============ Statistics Schemas ============


class ReportStatistics(BaseModel):
    """报告单统计"""

    total_count: int = 0
    draft_count: int = 0
    completed_count: int = 0
    approved_count: int = 0
    by_template: dict = {}
