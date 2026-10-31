"""AI 交互日志的响应 schema。

AI 问答（ChatRequest）、AI 出题（ExamExportRequest）、AI 查询规划（QueryPlan）
相关 schema 随对应 API 一并下线，此处仅保留日志查询所需模型。
"""

from pydantic import BaseModel, Field


class AiLogItem(BaseModel):
    """单条 AI 交互日志"""

    id: str = Field(..., description="日志 ID")
    bill_no: str | None = Field(None, description="关联单据编号")
    operate_type: str = Field(..., description="操作类型")
    operator: str = Field(..., description="操作人账号")
    system_prompt: str | None = Field(None, description="系统提示词")
    user_input: str | None = Field(None, description="用户输入内容")
    ai_response: str | None = Field(None, description="AI 返回内容")
    error_message: str | None = Field(None, description="错误信息")
    tokens_used: int | None = Field(None, description="使用的 token 数量")
    latency_ms: int | None = Field(None, description="响应耗时（毫秒）")
    created_at: str = Field(..., description="创建时间")


class AiLogPaginatedListResponse(BaseModel):
    """AI 交互日志分页数据"""

    items: list[AiLogItem] = Field(default_factory=list, description="日志列表")
    total: int = Field(0, description="总条数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")


class AiLogPaginatedListApiResponse(BaseModel):
    """AI 交互日志分页 API 响应信封"""

    code: int = 200
    message: str = "success"
    data: AiLogPaginatedListResponse | None = None


class AiLogDetailApiResponse(BaseModel):
    """AI 交互日志详情 API 响应信封"""

    code: int = 200
    message: str = "success"
    data: AiLogItem | None = None
