"""SOP AI 模块 Pydantic Schemas

定义所有请求和响应的数据模型。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============ 配置相关 Schemas ============


class SopAiConfigBase(BaseModel):
    """配置基础模型"""

    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="配置描述")


class SopAiConfigCreate(SopAiConfigBase):
    """创建配置"""

    operator: Optional[str] = Field(None, description="操作人")


class SopAiConfigUpdate(BaseModel):
    """更新配置"""

    config_value: str = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="配置描述")
    operator: Optional[str] = Field(None, description="操作人")


class SopAiConfigResponse(SopAiConfigBase):
    """配置响应模型"""

    id: str = Field(..., description="ID")
    operator: Optional[str] = Field(None, description="操作人")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


# ============ 校验相关 Schemas ============


class SingleCheckRequest(BaseModel):
    """单文件预审请求"""

    file_path: str = Field(..., description="文件路径")
    file_name: str = Field(..., description="文件名")
    check_type: str = Field("single", description="校验类型")
    operator: Optional[str] = Field(None, description="操作人")


class BatchCheckRequest(BaseModel):
    """批量巡检请求"""

    file_paths: list[str] = Field(..., description="文件路径列表")
    check_type: str = Field("batch", description="校验类型")
    operator: Optional[str] = Field(None, description="操作人")


class CheckResultBase(BaseModel):
    """校验结果基础模型"""

    problem_type: Optional[str] = Field(None, description="问题类型")
    risk_level: Optional[str] = Field(None, description="风险等级")
    location: Optional[str] = Field(None, description="问题位置")
    description: Optional[str] = Field(None, description="问题描述")
    source_file: Optional[str] = Field(None, description="源文件")
    suggestion: Optional[str] = Field(None, description="整改建议")


class CheckResultCreate(CheckResultBase):
    """创建校验结果"""

    main_id: str = Field(..., description="主记录ID")
    operator: Optional[str] = Field(None, description="操作人")


class CheckResultResponse(CheckResultBase):
    """校验结果响应模型"""

    id: str = Field(..., description="ID")
    main_id: str = Field(..., description="主记录ID")
    handle_status: str = Field(..., description="处理状态")
    ignore_reason: Optional[str] = Field(None, description="忽略原因")
    operator: Optional[str] = Field(None, description="操作人")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class CheckMainBase(BaseModel):
    """校验主表基础模型"""

    file_code: Optional[str] = Field(None, description="文件编号")
    file_name: Optional[str] = Field(None, description="文件名")
    file_type: Optional[str] = Field(None, description="文件类型")
    check_type: Optional[str] = Field(None, description="校验类型")


class CheckMainCreate(CheckMainBase):
    """创建校验主记录"""

    operator: Optional[str] = Field(None, description="操作人")


class CheckMainUpdate(BaseModel):
    """更新校验主记录"""

    status: Optional[str] = Field(None, description="状态")
    result_summary: Optional[str] = Field(None, description="结果摘要")
    total_problems: Optional[int] = Field(None, description="问题总数")
    risk_high: Optional[int] = Field(None, description="高风险数")
    risk_medium: Optional[int] = Field(None, description="中风险数")
    risk_low: Optional[int] = Field(None, description="低风险数")


class CheckMainResponse(CheckMainBase):
    """校验主记录响应模型"""

    id: str = Field(..., description="ID")
    status: str = Field(..., description="状态")
    result_summary: Optional[str] = Field(None, description="结果摘要")
    total_problems: int = Field(default=0, description="问题总数")
    risk_high: int = Field(default=0, description="高风险数")
    risk_medium: int = Field(default=0, description="中风险数")
    risk_low: int = Field(default=0, description="低风险数")
    operator: Optional[str] = Field(None, description="操作人")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class CheckMainDetailResponse(CheckMainResponse):
    """校验主记录详情响应模型（包含问题列表）"""

    problems: list[CheckResultResponse] = Field(default_factory=list, description="问题列表")

    class Config:
        from_attributes = True


# ============ 定时任务相关 Schemas ============


class ScheduledJobBase(BaseModel):
    """定时任务基础模型"""

    job_id: str = Field(..., description="任务ID")
    job_name: str = Field(..., description="任务名称")
    cron_expression: str = Field(..., description="Cron 表达式")
    file_pattern: str = Field(..., description="文件匹配模式")
    enabled: bool = Field(True, description="是否启用")


class ScheduledJobCreate(ScheduledJobBase):
    """创建定时任务"""

    operator: Optional[str] = Field(None, description="操作人")


class ScheduledJobUpdate(BaseModel):
    """更新定时任务"""

    job_name: Optional[str] = Field(None, description="任务名称")
    cron_expression: Optional[str] = Field(None, description="Cron 表达式")
    file_pattern: Optional[str] = Field(None, description="文件匹配模式")
    enabled: Optional[bool] = Field(None, description="是否启用")
    operator: Optional[str] = Field(None, description="操作人")


class ScheduledJobResponse(ScheduledJobBase):
    """定时任务响应模型"""

    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    last_run_time: Optional[datetime] = Field(None, description="上次运行时间")
    run_count: int = Field(default=0, description="运行次数")

    class Config:
        from_attributes = True


# ============ 问题处理 Schemas ============


class ProblemHandleRequest(BaseModel):
    """问题处理请求"""

    handle_status: str = Field(..., description="处理状态")
    ignore_reason: Optional[str] = Field(None, description="忽略原因")
    operator: Optional[str] = Field(None, description="操作人")


# ============ 通用响应 Schemas ============


class CheckTaskResponse(BaseModel):
    """校验任务响应"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="状态")
    message: Optional[str] = Field(None, description="消息")


class ApiResponse(BaseModel):
    """通用 API 响应"""

    code: int = Field(200, description="状态码")
    message: str = Field("success", description="消息")
    data: Optional[dict] = Field(None, description="数据")


class PaginatedResponse(BaseModel):
    """分页响应"""

    items: list = Field(default_factory=list, description="数据列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页")
    page_size: int = Field(20, description="每页数量")


# ============ 导出相关 Schemas ============


class ExportRequest(BaseModel):
    """导出请求"""

    format: str = Field("excel", description="导出格式: excel/pdf")
    include_problems: bool = Field(True, description="是否包含问题明细")