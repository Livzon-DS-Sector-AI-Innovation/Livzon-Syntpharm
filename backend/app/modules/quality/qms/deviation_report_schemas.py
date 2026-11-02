"""偏差报告 Schemas"""

from typing import Literal

from pydantic import BaseModel, Field

# 与 deviation_report_api._OPTIMIZE_PROMPTS 的键保持一致，由 OpenAPI 输出为 enum，
# 前端类型因此可以从生成 schema 派生，不再手写联合类型。
OptimizeType = Literal["polish", "summarize", "expand", "simplify"]


class OptimizeTextRequest(BaseModel):
    """AI优化文本请求"""

    text: str
    optimize_type: OptimizeType = "polish"


class SaveHtmlRequest(BaseModel):
    """保存HTML为Word请求"""

    file_id: str = Field(min_length=1)
    html_content: str


class DeviationReportUploadData(BaseModel):
    """Word 模板上传解析结果"""

    file_id: str = Field(description="原始文件标识")
    file_name: str = Field(description="原始文件名")
    html_content: str = Field(description="解析出的 HTML")
    file_path: str = Field(description="原始文件下载地址")
    warnings: list[str] = Field(default_factory=list, description="解析告警")


class DeviationOptimizeData(BaseModel):
    """AI 优化结果"""

    optimized_text: str


class DeviationOptimizeJobData(BaseModel):
    """AI 优化任务受理结果（202，任务在后台执行）"""

    job_id: str = Field(description="任务标识，用于轮询结果")
    status: str = Field(description="任务状态：pending/running")


class DeviationOptimizeJobResultData(BaseModel):
    """AI 优化任务状态（轮询用）"""

    job_id: str
    status: str = Field(description="任务状态：pending/running/done/failed")
    optimized_text: str | None = Field(default=None, description="status=done 时返回")
    error: str | None = Field(default=None, description="status=failed 时返回")
