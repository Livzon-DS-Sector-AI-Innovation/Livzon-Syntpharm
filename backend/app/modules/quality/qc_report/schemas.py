"""质量检验台账的请求/响应模型。

所有结构化响应的 envelope 都是具体模型（含 code / message / data），
禁止 `response_model=dict` 或 `ApiResponse`，否则前端拿不到可靠类型。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CategoryLiteral = Literal["raw", "intermediate", "finished"]
ValueTypeLiteral = Literal["quant", "qual", "grade"]


# ── 品种 ────────────────────────────────────────────────
class QcProductCreate(BaseModel):
    """仅建品种（不上传文件）。"""

    name: str = Field(..., min_length=1, max_length=200, description="品种名称")
    abbr: str = Field(..., min_length=2, max_length=16, description="品名缩写，批号前缀")
    category: CategoryLiteral = Field(..., description="物料分类")
    quality_standard: str | None = Field(default=None, max_length=255, description="质量标准")
    status: str = Field(default="active", description="状态")


class QcProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    abbr: str | None = Field(default=None, min_length=2, max_length=16)
    category: CategoryLiteral | None = None
    quality_standard: str | None = Field(default=None, max_length=255)
    status: str | None = None


class QcProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    abbr: str
    category: str
    quality_standard: str | None
    source_file_name: str | None
    status: str
    last_inspected_at: datetime | None
    created_at: datetime
    updated_at: datetime


class QcProductListItem(BaseModel):
    """品种列表行，含批次统计。"""

    id: uuid.UUID
    name: str
    abbr: str
    category: str
    quality_standard: str | None
    status: str
    last_inspected_at: datetime | None
    batch_count: int = 0
    normal_count: int = 0
    oos_count: int = 0
    internal_count: int = 0
    trend_count: int = 0
    pending_count: int = 0
    pass_rate: float = 0.0
    top_level: str = "pending"


class QcProductListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[QcProductListItem]
    meta: dict[str, object] | None = None


class QcProductApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcProductResponse


class QcStandardSourceItem(BaseModel):
    """某一层的标准最终取自哪份文件，供导入完成页核对。"""

    column_letter: str
    item_name: str
    layer: str
    layer_label: str
    final_text: str | None = None
    source: str = Field(..., description="excel 结果表 / docx 标准表 / none 留空")
    from_choice: bool = Field(default=False, description="True=按人工裁决，False=默认取值")


class QcBatchImportResult(BaseModel):
    created_count: int = 0
    skipped_count: int = 0
    skipped_batch_nos: list[str] = Field(default_factory=list)
    level_counts: dict[str, int] = Field(default_factory=dict)


class QcBatchImportApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcBatchImportResult


class QcDeleteResponse(BaseModel):
    id: uuid.UUID
    deleted: bool = True


class QcDeleteApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcDeleteResponse


# ── 检验项目 ────────────────────────────────────────────
class QcItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    item_no: int
    item_name: str
    standard_item_name: str | None = None
    standard_source: str | None = None
    column_group_start: int | None = None
    sub_label: str | None = None
    value_type: str
    unit: str | None
    legal_text: str | None
    internal_text: str | None
    sigma_text: str | None
    source_column: str | None
    is_record_only: bool
    sigma_basis_period: str | None
    sigma_updated_by: uuid.UUID | None
    sigma_updated_at: datetime | None
    sort_order: int
    is_enabled: bool


class QcItemUpdate(BaseModel):
    """修改标准原文（限值以文本保存，不拆上下限）。"""

    legal_text: str | None = None
    internal_text: str | None = None
    sigma_text: str | None = None
    sigma_basis_period: str | None = Field(default=None, max_length=32)
    is_enabled: bool | None = None


class QcItemListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[QcItemResponse]


class QcItemApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcItemResponse


# ── 导入 ────────────────────────────────────────────────
class QcImportPreviewItem(BaseModel):
    """解析出的检验项目及其匹配情况。"""

    item_no: int
    item_name: str
    value_type: str
    unit: str | None
    legal_text: str | None
    internal_text: str | None
    sigma_text: str | None
    matched_column: str | None = Field(default=None, description="自动匹配到的结果表列名")
    match_kind: str = Field(default="pending", description="saved / exact / contain / pending")
    candidates: list[str] = Field(default_factory=list, description="需要人工指认时的候选列")


class QcImportExtraColumn(BaseModel):
    """结果表有、标准表没有的列，将建成「仅记录」项目。"""

    column_index: int
    column_name: str


class QcUnmatchedCandidate(BaseModel):
    """待指定的候选列。用列字母区分同名列。"""

    letter: str
    name: str


class QcUnmatchedItem(BaseModel):
    """标准表里有、但没能自动对上结果表列的项目，可由人工点一次指定。"""

    item_name: str
    candidates: list[QcUnmatchedCandidate] = Field(default_factory=list)
    docx_legal_text: str | None = None
    docx_internal_text: str | None = None
    docx_sigma_text: str | None = None
    matched_column_letter: str | None = Field(default=None, description="当前已对应的列字母；未对应为 None")
    matched_column_name: str | None = Field(default=None, description="当前已对应的列名")


class QcStandardConflict(BaseModel):
    """两份文件对同一层标准的写法不一致，交由人工判断。"""

    column_index: int
    column_letter: str
    item_name: str
    layer: str = Field(..., description="legal / internal / sigma")
    layer_label: str
    excel_text: str | None = None
    docx_text: str | None = None
    note: str | None = None
    severity: str = Field(
        default="text",
        description="numeric 数值范围不同（必须确认）/ text 仅文字表述不同（默认采用结果表）",
    )


class QcImportSummary(BaseModel):
    total_columns: int
    same_count: int
    conflict_count: int
    only_excel_count: int
    skipped_standard_items: list[str] = Field(default_factory=list)


class QcImportPreviewResponse(BaseModel):
    docx_file_name: str
    xlsx_file_name: str
    sheet_title: str
    batch_count: int
    data_start_row: int
    column_count: int
    product_name_suggestion: str
    abbr_suggestion: str
    quality_standard_suggestion: str | None
    items: list[QcImportPreviewItem]
    extra_columns: list[QcImportExtraColumn]
    batch_no_samples: list[str]
    sample_values: list[dict[str, str | None]]
    unrecognized_items: list[str] = Field(default_factory=list, description="三层标准都解析不出数值的项目，需人工补")
    conflicts: list[QcStandardConflict] = Field(
        default_factory=list, description="两份文件写法不一致、需人工逐条判断的标准"
    )
    unmatched_items: list[QcUnmatchedItem] = Field(
        default_factory=list, description="标准表有、但没能自动对上结果表列的项目"
    )
    summary: QcImportSummary | None = Field(default=None, description="交叉印证统计：一致 / 待确认 / 仅结果表有")


class QcImportPreviewApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcImportPreviewResponse


class QcImportCommitResponse(BaseModel):
    product_id: uuid.UUID
    product_name: str
    item_count: int
    record_only_count: int
    batch_count: int
    value_count: int
    unrecognized_items: list[str]
    skipped_standard_items: list[str] = Field(
        default_factory=list,
        description="标准表里有、但结果表找不到对应列的项目，未建档",
    )
    resolved_conflicts: int = Field(default=0, description="本次按人工选择落地的冲突层数")
    standard_sources: list[QcStandardSourceItem] = Field(
        default_factory=list,
        description="两份文件不一致的层，最终用了哪份的值、是否人工裁决",
    )


class QcImportCommitApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcImportCommitResponse


# ── 批次与实测值 ────────────────────────────────────────
class QcBatchRow(BaseModel):
    """一行批次，values/levels 以 item_id 为键，前端按项目顺序渲染列。"""

    id: uuid.UUID
    batch_no: str
    level: str
    note: str | None
    entered_by_name: str | None
    source: str
    created_at: datetime
    values: dict[str, str | None] = Field(default_factory=dict)
    levels: dict[str, str] = Field(default_factory=dict)


class QcBatchPageData(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[QcBatchRow]


class QcBatchPageApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcBatchPageData


class QcBatchCreate(BaseModel):
    """手工新增一批。"""

    batch_no: str = Field(..., min_length=1, max_length=64)
    note: str | None = None
    values: dict[str, str] = Field(default_factory=dict, description="item_id -> 实测值")


class QcBatchApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcBatchRow


# ── 统计 ────────────────────────────────────────────────
class QcStatsResponse(BaseModel):
    total: int = 0
    oos: int = 0
    internal: int = 0
    trend: int = 0
    normal: int = 0
    skip: int = 0
    pending: int = 0


class QcStatsApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcStatsResponse


class QcAttentionBatch(BaseModel):
    product_id: uuid.UUID
    product_name: str
    batch_id: uuid.UUID
    batch_no: str
    level: str
    reason: str | None = None


class QcAttentionBatchListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[QcAttentionBatch]


class QcRejudgeResponse(BaseModel):
    product_id: uuid.UUID
    batch_count: int
    value_count: int
    changed_batch_count: int = Field(description="有任一单元格判定变化的批次数")
    changed_value_count: int = Field(default=0, description="判定发生变化的检验值条数")


class QcRejudgeApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: QcRejudgeResponse


__all__ = [
    "QcProductCreate",
    "QcProductUpdate",
    "QcProductResponse",
    "QcProductListItem",
    "QcProductListApiResponse",
    "QcProductApiResponse",
    "QcDeleteResponse",
    "QcDeleteApiResponse",
    "QcItemResponse",
    "QcItemUpdate",
    "QcItemListApiResponse",
    "QcItemApiResponse",
    "QcImportPreviewItem",
    "QcImportExtraColumn",
    "QcImportPreviewResponse",
    "QcImportPreviewApiResponse",
    "QcImportCommitResponse",
    "QcImportCommitApiResponse",
    "QcBatchRow",
    "QcBatchPageData",
    "QcBatchPageApiResponse",
    "QcBatchCreate",
    "QcBatchApiResponse",
    "QcStatsResponse",
    "QcStatsApiResponse",
    "QcAttentionBatch",
    "QcAttentionBatchListApiResponse",
    "QcRejudgeResponse",
    "QcRejudgeApiResponse",
]
