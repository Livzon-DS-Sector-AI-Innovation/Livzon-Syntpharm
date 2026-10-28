"""Doc Check 模块请求/响应模型。

字段与 quality.sop_ai_check_main / quality.sop_ai_check_problem 表的真实列一一对应，
避免出现表中不存在的字段（历史版本的 problem_no/category/severity/title 等列并不存在）。
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.schemas import PaginationMeta

CheckStatusValue = Literal["pending", "running", "completed", "failed", "cancelled"]
CheckTypeValue = Literal["single", "batch", "scheduled"]
ProblemTypeValue = Literal["duplicate", "conflict", "compliance", "format", "content"]
RiskLevelValue = Literal["high", "medium", "low"]
HandleStatusValue = Literal["pending", "confirmed", "ignored", "fixed"]


def _normalize_enum(value: Any) -> Any:
    """把 StrEnum 成员或大写枚举名归一化为小写字符串。"""
    if isinstance(value, str):
        return value.lower()
    return getattr(value, "value", value)


# ============ 配置 ============


class DocCheckConfigCreate(BaseModel):
    """新增配置项"""

    config_key: str = Field(..., min_length=1, max_length=100, description="配置键")
    config_value: str = Field(..., min_length=1, description="配置值")
    description: str | None = Field(None, max_length=500, description="配置说明")


class DocCheckConfigUpdate(BaseModel):
    """修改配置项"""

    config_value: str | None = Field(None, min_length=1, description="配置值")
    description: str | None = Field(None, max_length=500, description="配置说明")


class DocCheckConfigResponse(BaseModel):
    """配置项"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    config_key: str
    config_value: str
    description: str | None = None
    is_enabled: bool = True
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============ 校验任务 ============


class DocCheckCreate(BaseModel):
    """创建校验任务"""

    doc_type: str = Field(..., min_length=1, max_length=50, description="文件类型，如 SOP")
    doc_title: str = Field(..., min_length=1, max_length=500, description="文件名称")
    check_type: CheckTypeValue = Field("single", description="校验类型")


class DocCheckUpdate(BaseModel):
    """修改校验任务（仅待处理状态可改）"""

    doc_type: str | None = Field(None, min_length=1, max_length=50)
    doc_title: str | None = Field(None, min_length=1, max_length=500)
    check_type: CheckTypeValue | None = None

    @field_validator("check_type", mode="before")
    @classmethod
    def _lower_check_type(cls, value: Any) -> Any:
        return _normalize_enum(value)


class DocCheckExecuteRequest(BaseModel):
    """执行校验：二选一提供上传文件标识或直接文本内容"""

    file_id: str | None = Field(None, max_length=64, description="上传接口返回的文件标识")
    doc_content: str | None = Field(None, description="直接提交的文档正文")

    @model_validator(mode="after")
    def _require_one_source(self) -> "DocCheckExecuteRequest":
        if not self.file_id and not self.doc_content:
            raise ValueError("file_id 与 doc_content 至少提供一个")
        return self


class DocCheckBatchCreate(BaseModel):
    """批量创建校验任务"""

    file_ids: list[str] = Field(..., min_length=1, max_length=50, description="文件标识列表")
    check_type: CheckTypeValue = "batch"


class DocCheckResponse(BaseModel):
    """校验任务"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    file_code: str | None = None
    file_name: str | None = None
    file_type: str | None = None
    check_type: str | None = None
    status: str
    result_summary: str | None = None
    total_problems: int = 0
    risk_high: int = 0
    risk_medium: int = 0
    risk_low: int = 0
    operator: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _lower_status(cls, value: Any) -> Any:
        return _normalize_enum(value)


class ProblemResponse(BaseModel):
    """问题明细"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    main_id: str
    problem_type: str | None = None
    risk_level: str | None = None
    location: str | None = None
    description: str | None = None
    source_file: str | None = None
    suggestion: str | None = None
    handle_status: str
    ignore_reason: str | None = None
    operator: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("problem_type", "risk_level", "handle_status", mode="before")
    @classmethod
    def _lower_enum_fields(cls, value: Any) -> Any:
        return _normalize_enum(value)


class DocCheckDetailResponse(DocCheckResponse):
    """校验任务详情（含问题明细）"""

    problems: list[ProblemResponse] = Field(default_factory=list)


class DocCheckTaskResponse(BaseModel):
    """任务提交结果"""

    check_id: str
    status: str
    job_id: str | None = None


class DocCheckProgressResponse(BaseModel):
    """任务进度"""

    check_id: str
    status: str
    progress: int = Field(..., ge=0, le=100)
    current_step: str


class DocCheckBatchResponse(BaseModel):
    """批量创建结果"""

    created: int
    skipped: list[str] = Field(default_factory=list)
    check_ids: list[str] = Field(default_factory=list)


class DocCheckConfirmResponse(BaseModel):
    """确认通过结果"""

    check_id: str
    status: str
    confirmed_problems: int


class DocCheckExportResponse(BaseModel):
    """导出结果"""

    file_name: str
    download_url: str
    format: str


# ============ 上传 ============


class DocCheckUploadResponse(BaseModel):
    """上传结果"""

    file_id: str
    file_name: str
    file_size: int
    content_type: str


class DocCheckUploadProgressResponse(BaseModel):
    """上传进度（同步落盘，返回即完成）"""

    file_id: str
    status: str
    progress: int = Field(..., ge=0, le=100)


# ============ 问题处理 ============


class ProblemUpdate(BaseModel):
    """处理单个问题"""

    handle_status: HandleStatusValue
    ignore_reason: str | None = Field(None, description="忽略原因，handle_status=ignored 时必填")

    @field_validator("handle_status", mode="before")
    @classmethod
    def _lower_handle_status(cls, value: Any) -> Any:
        return _normalize_enum(value)


class ProblemBatchUpdate(BaseModel):
    """批量处理问题"""

    problem_ids: list[str] = Field(..., min_length=1, max_length=200)
    handle_status: HandleStatusValue
    ignore_reason: str | None = None

    @field_validator("handle_status", mode="before")
    @classmethod
    def _lower_handle_status(cls, value: Any) -> Any:
        return _normalize_enum(value)


class ProblemBatchResult(BaseModel):
    """批量处理结果"""

    updated: int
    skipped: list[str] = Field(default_factory=list)


# ============ 响应信封 ============


class DocCheckConfigListApiResponse(BaseModel):
    """配置列表响应包装"""

    code: int = 200
    message: str = "success"
    data: list[DocCheckConfigResponse]


class DocCheckConfigApiResponse(BaseModel):
    """单条配置响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckConfigResponse


class DocCheckListApiResponse(BaseModel):
    """校验任务列表响应包装"""

    code: int = 200
    message: str = "success"
    data: list[DocCheckResponse]
    meta: PaginationMeta | None = None


class DocCheckApiResponse(BaseModel):
    """校验任务响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckResponse


class DocCheckDetailApiResponse(BaseModel):
    """校验任务详情响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckDetailResponse


class DocCheckTaskApiResponse(BaseModel):
    """任务提交响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckTaskResponse


class DocCheckProgressApiResponse(BaseModel):
    """任务进度响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckProgressResponse


class DocCheckBatchApiResponse(BaseModel):
    """批量创建响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckBatchResponse


class DocCheckConfirmApiResponse(BaseModel):
    """确认通过响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckConfirmResponse


class DocCheckExportApiResponse(BaseModel):
    """导出响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckExportResponse


class DocCheckUploadApiResponse(BaseModel):
    """上传响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckUploadResponse


class DocCheckUploadProgressApiResponse(BaseModel):
    """上传进度响应包装"""

    code: int = 200
    message: str = "success"
    data: DocCheckUploadProgressResponse


class ProblemListApiResponse(BaseModel):
    """问题列表响应包装"""

    code: int = 200
    message: str = "success"
    data: list[ProblemResponse]


class ProblemApiResponse(BaseModel):
    """单条问题响应包装"""

    code: int = 200
    message: str = "success"
    data: ProblemResponse


class ProblemBatchApiResponse(BaseModel):
    """批量处理响应包装"""

    code: int = 200
    message: str = "success"
    data: ProblemBatchResult


class MessageApiResponse(BaseModel):
    """无数据响应包装"""

    code: int = 200
    message: str = "success"
    data: None = None
