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
