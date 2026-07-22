"""偏差报告 Schemas"""

from pydantic import BaseModel


class OptimizeTextRequest(BaseModel):
    """AI优化文本请求"""

    text: str
    optimize_type: str = "polish"
