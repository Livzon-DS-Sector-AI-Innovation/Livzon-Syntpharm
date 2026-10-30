"""偏差报告 Schemas"""

from pydantic import BaseModel, Field


class OptimizeTextRequest(BaseModel):
    """AI优化文本请求"""

    text: str
    optimize_type: str = "polish"


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
