"""Safety request and response schemas for Feishu integration."""

from typing import Any

from pydantic import BaseModel, Field


class FeishuWsStatusResponse(BaseModel):
    """Feishu WebSocket status response"""

    connected: bool = Field(..., description="WebSocket 是否存活")
    subscription_ok: bool = Field(..., description="Bitable 文档事件订阅是否成功")
    registered_events: list[str] = Field(default_factory=list, description="已注册的事件类型")
    frame_stats: dict[str, Any] = Field(default_factory=dict, description="帧活动统计")
    last_pong_seconds_ago: int | None = Field(None, description="距最后一次 PONG 的秒数")
    pong_watchdog_healthy: bool | None = Field(None, description="PONG 看门狗是否健康")


class FeishuWsRestartResponse(BaseModel):
    """Feishu WebSocket restart response"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")


# ============ API Response Wrappers ============


class FeishuWsStatusApiResponse(BaseModel):
    """Feishu WebSocket status response wrapper"""

    code: int = 200
    message: str = "success"
    data: FeishuWsStatusResponse | None = None


class FeishuWsRestartApiResponse(BaseModel):
    """Feishu WebSocket restart response wrapper"""

    code: int = 200
    message: str = "success"
    data: FeishuWsRestartResponse | None = None
