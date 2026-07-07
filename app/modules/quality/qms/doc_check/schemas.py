"""Doc Check 模块请求/响应 Schema

定义文档合规校验 API 的请求和响应数据结构。
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class CheckStatus(str, Enum):
    """校验状态"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProblemSeverity(str, Enum):
    """问题严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ProblemCategory(str, Enum):
    """问题分类"""

    FORMAT = "format"
    CONTENT = "content"
    COMPLIANCE = "compliance"
    LOGIC = "logic"
    MISSING = "missing"


# ============ 配置 Schema ============


class DocCheckConfigBase(BaseModel):
    """文档校验配置基础模式（与 SopAiConfig 匹配）"""

    config_key: str = Field(..., max_length=100, description="配置键")
    config_value: str = Field(..., description="配置值")
    description: str | None = Field(None, max_length=500, description="描述")


class DocCheckConfigCreate(DocCheckConfigBase):
    """创建配置"""
    pass


class DocCheckConfigUpdate(BaseModel):
    """更新配置"""

    config_value: str | None = Field(None, description="配置值")
    description: str | None = Field(None, max_length=500, description="描述")


class DocCheckConfigResponse(BaseModel):
    """配置响应（与 SopAiConfig 匹配）"""

    id: str | None = None
    config_key: str
    config_value: str
    description: str | None = None
    operator: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def convert_uuid_to_str(cls, data):
        """将 UUID 对象转换为字符串"""
        if hasattr(data, "__dict__"):
            # SQLAlchemy 模型对象
            data = data.__dict__.copy()
        if isinstance(data, dict):
            if "id" in data and hasattr(data["id"], "hex"):
                data["id"] = str(data["id"])
            if "created_at" in data and data["created_at"]:
                data["created_at"] = data["created_at"].isoformat()
            if "updated_at" in data and data["updated_at"]:
                data["updated_at"] = data["updated_at"].isoformat()
        return data


# ============ 校验主表 Schema ============


class DocCheckCreate(BaseModel):
    """创建校验任务"""

    doc_type: str = Field("SOP", max_length=50, description="文档类型")
    doc_title: str | None = Field(None, max_length=255, description="文档标题")
    doc_content: str | None = Field(None, description="文档内容")
    file_id: str | None = Field(None, description="上传文件ID")
    check_config: dict | None = Field(None, description="校验配置(前端扩展字段)")


class DocCheckUpdate(BaseModel):
    """更新校验任务"""

    doc_type: str | None = Field(None, max_length=50, description="文档类型")
    doc_title: str | None = Field(None, max_length=255, description="文档标题")
    doc_content: str | None = Field(None, description="文档内容")
    status: str | None = Field(None, description="校验状态")


class ProblemItem(BaseModel):
    """问题明细"""

    problem_no: int = Field(..., description="问题序号")
    category: ProblemCategory = Field(..., description="问题分类")
    severity: ProblemSeverity = Field(..., description="严重程度")
    title: str = Field(..., max_length=255, description="问题标题")
    description: str = Field(..., description="问题描述")
    location: str | None = Field(None, max_length=255, description="位置信息")
    suggestion: str | None = Field(None, description="改进建议")
    reference: str | None = Field(None, description="参考依据")


class CheckResult(BaseModel):
    """校验结果"""

    status: CheckStatus = Field(..., description="校验状态")
    check_result: str | None = Field(None, description="校验结果(JSON)")
    ai_suggestion: str | None = Field(None, description="AI 改进建议")
    problem_count: int = Field(0, description="问题数量")
    critical_count: int = Field(0, description="严重问题数量")
    error_count: int = Field(0, description="错误数量")
    warning_count: int = Field(0, description="警告数量")
    problems: list[ProblemItem] = Field(default_factory=list, description="问题列表")


class DocCheckResponse(BaseModel):
    """校验任务响应"""

    id: uuid.UUID
    file_code: str | None = None
    file_name: str | None = None
    file_type: str | None = None
    status: CheckStatus
    result_summary: str | None = None
    total_problems: int = 0
    risk_high: int = 0
    risk_medium: int = 0
    risk_low: int = 0
    operator: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class DocCheckDetailResponse(DocCheckResponse):
    """校验任务详情响应(含问题列表)"""

    problems: list[ProblemItem] = Field(default_factory=list, description="问题列表")

    class Config:
        from_attributes = True


# ============ 问题明细 Schema ============


class ProblemBase(BaseModel):
    """问题基础模式"""

    problem_no: int = Field(..., description="问题序号")
    category: ProblemCategory = Field(..., description="问题分类")
    severity: ProblemSeverity = Field(..., description="严重程度")
    title: str = Field(..., max_length=255, description="问题标题")
    description: str = Field(..., description="问题描述")
    location: str | None = Field(None, max_length=255, description="位置信息")
    suggestion: str | None = Field(None, description="改进建议")
    reference: str | None = Field(None, description="参考依据")


class ProblemResponse(ProblemBase):
    """问题响应"""

    id: uuid.UUID
    check_main_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProblemUpdate(BaseModel):
    """问题更新请求"""

    handle_status: str | None = Field(None, description="处理状态")
    ignore_reason: str | None = Field(None, description="忽略原因")
    operator: str | None = Field(None, description="操作人")


# ============ 向量缓存 Schema ============


class VectorCacheResponse(BaseModel):
    """向量缓存响应"""

    id: uuid.UUID
    doc_type: str
    doc_hash: str
    doc_title: str | None = None
    doc_summary: str | None = None
    content_vector: list[float]
    vector_storage_type: str
    hit_count: int
    last_hit_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True