"""SOP AI 模块 Pydantic Schemas

定义所有请求和响应的数据模型。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ============ 配置相关 Schemas ============


class SopAiConfigBase(BaseModel):
    """配置基础模型"""

    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值")
    description: str | None = Field(None, description="配置描述")


class SopAiConfigCreate(SopAiConfigBase):
    """创建配置"""

    operator: str | None = Field(None, description="操作人")


class SopAiConfigUpdate(BaseModel):
    """更新配置"""

    config_value: str = Field(..., description="配置值")
    description: str | None = Field(None, description="配置描述")
    operator: str | None = Field(None, description="操作人")


class SopAiConfigResponse(SopAiConfigBase):
    """配置响应模型"""

    id: str = Field(..., description="ID")
    operator: str | None = Field(None, description="操作人")
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
    operator: str | None = Field(None, description="操作人")


class BatchCheckRequest(BaseModel):
    """批量巡检请求"""

    file_paths: list[str] = Field(..., description="文件路径列表")
    check_type: str = Field("batch", description="校验类型")
    operator: str | None = Field(None, description="操作人")


class CheckResultBase(BaseModel):
    """校验结果基础模型"""

    problem_type: str | None = Field(None, description="问题类型")
    risk_level: str | None = Field(None, description="风险等级")
    location: str | None = Field(None, description="问题位置")
    description: str | None = Field(None, description="问题描述")
    source_file: str | None = Field(None, description="源文件")
    suggestion: str | None = Field(None, description="整改建议")


class CheckResultCreate(CheckResultBase):
    """创建校验结果"""

    main_id: str = Field(..., description="主记录ID")
    operator: str | None = Field(None, description="操作人")


class CheckResultResponse(CheckResultBase):
    """校验结果响应模型"""

    id: str = Field(..., description="ID")
    main_id: str = Field(..., description="主记录ID")
    handle_status: str = Field(..., description="处理状态")
    ignore_reason: str | None = Field(None, description="忽略原因")
    operator: str | None = Field(None, description="操作人")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class CheckMainBase(BaseModel):
    """校验主表基础模型"""

    file_code: str | None = Field(None, description="文件编号")
    file_name: str | None = Field(None, description="文件名")
    file_type: str | None = Field(None, description="文件类型")
    check_type: str | None = Field(None, description="校验类型")


class CheckMainCreate(CheckMainBase):
    """创建校验主记录"""

    operator: str | None = Field(None, description="操作人")


class CheckMainUpdate(BaseModel):
    """更新校验主记录"""

    status: str | None = Field(None, description="状态")
    result_summary: str | None = Field(None, description="结果摘要")
    total_problems: int | None = Field(None, description="问题总数")
    risk_high: int | None = Field(None, description="高风险数")
    risk_medium: int | None = Field(None, description="中风险数")
    risk_low: int | None = Field(None, description="低风险数")


class CheckMainResponse(CheckMainBase):
    """校验主记录响应模型"""

    id: str = Field(..., description="ID")
    status: str = Field(..., description="状态")
    result_summary: str | None = Field(None, description="结果摘要")
    total_problems: int = Field(default=0, description="问题总数")
    risk_high: int = Field(default=0, description="高风险数")
    risk_medium: int = Field(default=0, description="中风险数")
    risk_low: int = Field(default=0, description="低风险数")
    operator: str | None = Field(None, description="操作人")
    # quality.sop_ai_check_main 的 created_at / updated_at 既没有 server_default，
    # 模型里也没有 Python 端默认值，实际写入后为 NULL。声明成必填会在返回时抛
    # ResponseValidationError（500），故允许 None。
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")

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

    operator: str | None = Field(None, description="操作人")


class ScheduledJobUpdate(BaseModel):
    """更新定时任务"""

    job_name: str | None = Field(None, description="任务名称")
    cron_expression: str | None = Field(None, description="Cron 表达式")
    file_pattern: str | None = Field(None, description="文件匹配模式")
    enabled: bool | None = Field(None, description="是否启用")
    operator: str | None = Field(None, description="操作人")


class ScheduledJobResponse(ScheduledJobBase):
    """定时任务响应模型"""

    next_run_time: datetime | None = Field(None, description="下次运行时间")
    last_run_time: datetime | None = Field(None, description="上次运行时间")
    run_count: int = Field(default=0, description="运行次数")

    class Config:
        from_attributes = True


# ============ 问题处理 Schemas ============


class ProblemHandleRequest(BaseModel):
    """问题处理请求"""

    handle_status: str = Field(..., description="处理状态")
    ignore_reason: str | None = Field(None, description="忽略原因")
    operator: str | None = Field(None, description="操作人")


# ============ 通用响应 Schemas ============


class CheckTaskResponse(BaseModel):
    """校验任务响应"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="状态")
    message: str | None = Field(None, description="消息")


class PaginatedResponse(BaseModel):
    """分页响应"""

    items: list[Any] = Field(default_factory=list, description="数据列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页")
    page_size: int = Field(20, description="每页数量")


# ============ 导出相关 Schemas ============


class ExportRequest(BaseModel):
    """导出请求"""

    format: str = Field("excel", description="导出格式: excel/pdf")
    include_problems: bool = Field(True, description="是否包含问题明细")


# ============ 各端点响应数据 Schemas ============
# AGENTS.md:133 禁止裸 dict / Any 作为响应体，这里为每个端点补具体模型。


class SopAiConfigValue(BaseModel):
    """单个配置项的值"""

    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值")


class SopAiConfigUpdateResult(BaseModel):
    """配置更新结果"""

    id: str = Field(..., description="ID")
    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值")
    description: str | None = Field(None, description="配置描述")


class DetectedProblem(BaseModel):
    """本次校验检出的问题

    来自内存中的检测结果，尚未落库；字段随来源（查重 / AI 冲突 / AI 合规）而定。
    """

    problem_type: str | None = Field(None, description="问题类型")
    risk_level: str | None = Field(None, description="风险等级")
    location: str | None = Field(None, description="问题位置")
    description: str | None = Field(None, description="问题描述")
    source_file: str | None = Field(None, description="源文件")
    suggestion: str | None = Field(None, description="整改建议")
    main_id: str | None = Field(None, description="所属主记录ID")
    operator: str | None = Field(None, description="操作人")


class SingleCheckResult(BaseModel):
    """单文件预审的汇总结果"""

    total_problems: int = Field(0, description="问题总数")
    risk_high: int = Field(0, description="高风险数")
    risk_medium: int = Field(0, description="中风险数")
    risk_low: int = Field(0, description="低风险数")
    problems: list[DetectedProblem] = Field(default_factory=list, description="问题明细")


class SingleCheckResponse(BaseModel):
    """单文件预审响应（文件解析失败时只有 message，没有 result）"""

    task_id: str = Field(..., description="任务ID（即校验记录ID）")
    status: str = Field(..., description="状态")
    message: str | None = Field(None, description="文件解析失败时的原因")
    result: SingleCheckResult | None = Field(None, description="汇总结果")


class BatchFileResult(BaseModel):
    """批量巡检中单个文件的结果"""

    file_path: str = Field(..., description="文件路径")
    status: str = Field(..., description="状态")
    message: str | None = Field(None, description="失败原因")
    task_id: str | None = Field(None, description="校验记录ID")
    total_problems: int | None = Field(None, description="问题总数")
    risk_high: int | None = Field(None, description="高风险数")
    risk_medium: int | None = Field(None, description="中风险数")
    risk_low: int | None = Field(None, description="低风险数")


class BatchCheckResult(BaseModel):
    """批量巡检的汇总结果"""

    total_files: int = Field(0, description="文件总数")
    total_problems: int = Field(0, description="问题总数")
    file_results: list[BatchFileResult] = Field(default_factory=list, description="逐文件结果")


class BatchCheckResponse(BaseModel):
    """批量巡检响应"""

    task_id: str = Field(..., description="批次ID")
    status: str = Field(..., description="状态")
    result: BatchCheckResult = Field(..., description="汇总结果")


class CheckRecordPage(BaseModel):
    """校验记录分页"""

    items: list[CheckMainResponse] = Field(default_factory=list, description="记录列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页")
    page_size: int = Field(20, description="每页数量")


class ProblemDetail(BaseModel):
    """已落库的问题明细"""

    id: str = Field(..., description="ID")
    problem_type: str | None = Field(None, description="问题类型")
    risk_level: str | None = Field(None, description="风险等级")
    location: str | None = Field(None, description="问题位置")
    description: str | None = Field(None, description="问题描述")
    source_file: str | None = Field(None, description="源文件")
    suggestion: str | None = Field(None, description="整改建议")
    handle_status: str = Field(..., description="处理状态")
    ignore_reason: str | None = Field(None, description="忽略原因")
    operator: str | None = Field(None, description="操作人")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")


class CheckRecordDetail(BaseModel):
    """校验记录详情（含问题列表）"""

    id: str = Field(..., description="ID")
    file_code: str | None = Field(None, description="文件编号")
    file_name: str | None = Field(None, description="文件名")
    file_type: str | None = Field(None, description="文件类型")
    check_type: str | None = Field(None, description="校验类型")
    status: str = Field(..., description="状态")
    result_summary: str | None = Field(None, description="结果摘要")
    total_problems: int = Field(0, description="问题总数")
    risk_high: int = Field(0, description="高风险数")
    risk_medium: int = Field(0, description="中风险数")
    risk_low: int = Field(0, description="低风险数")
    operator: str | None = Field(None, description="操作人")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")
    problems: list[ProblemDetail] = Field(default_factory=list, description="问题列表")


class ProblemHandleResult(BaseModel):
    """问题处理结果"""

    id: str = Field(..., description="问题ID")
    handle_status: str = Field(..., description="处理状态")
    ignore_reason: str | None = Field(None, description="忽略原因")


class ScheduledJobListItem(BaseModel):
    """定时任务列表项"""

    job_id: str = Field(..., description="任务ID")
    job_name: str = Field(..., description="任务名称")
    cron_expression: str = Field(..., description="Cron 表达式")
    file_pattern: str = Field(..., description="文件匹配模式")
    enabled: bool = Field(True, description="是否启用")


class ScheduledJobDetail(BaseModel):
    """定时任务详情（新建任务时返回）"""

    job_id: str = Field(..., description="任务ID")
    job_name: str = Field(..., description="任务名称")
    cron_expression: str = Field(..., description="Cron 表达式")
    file_pattern: str = Field(..., description="文件匹配模式")
    enabled: bool = Field(True, description="是否启用")
    # ScheduledJob.to_dict() 输出的是 isoformat 字符串，不是 datetime。
    next_run_time: str | None = Field(None, description="下次运行时间（ISO 8601）")
    last_run_time: str | None = Field(None, description="上次运行时间（ISO 8601）")
    run_count: int = Field(0, description="运行次数")


class JobDeleteResult(BaseModel):
    """定时任务删除结果"""

    job_id: str = Field(..., description="任务ID")
    deleted: bool = Field(..., description="是否已删除")


class ExportReportResult(BaseModel):
    """导出报告回执"""

    id: str = Field(..., description="校验记录ID")
    format: str = Field(..., description="导出格式")
    download_url: str = Field(..., description="下载地址")
