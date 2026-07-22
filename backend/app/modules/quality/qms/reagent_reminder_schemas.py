"""试剂提醒管理 Schemas"""

from pydantic import BaseModel, Field


class ReminderConfigRequest(BaseModel):
    """提醒配置请求"""

    feishu_app_id: str = Field(..., description="飞书应用 AppID")
    feishu_app_secret: str = Field(..., description="飞书应用 AppSecret")
    feishu_chat_id: str = Field(..., description="飞书群 ID")
    low_stock_threshold: int = Field(default=2, description="库存不足阈值")
    is_enabled: bool = Field(default=True, description="是否启用")


class ItemReminderRequest(BaseModel):
    """单个试剂提醒配置请求"""

    reagent_name: str = Field(..., description="试剂名称")
    is_enabled: bool = Field(default=True, description="是否启用提醒")