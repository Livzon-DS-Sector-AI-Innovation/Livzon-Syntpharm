"""试剂提醒管理 Schemas"""

from uuid import UUID

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


# ============ 响应模型 ============
#
# `AGENTS.md:133` requires a concrete model per endpoint, describing the **full**
# body — `code`, `message` and `data`, not just `data`. These replace bare dict
# returns, which generated `{type: object}` in OpenAPI and gave the frontend no
# usable types.


class ReagentReminderConfigData(BaseModel):
    """The reminder config as the page reads it.

    `feishu_app_secret` is masked server-side — the column holds ciphertext, so the
    plaintext is never returned.
    """

    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    feishu_chat_id: str | None = None
    low_stock_threshold: int | None = None
    is_enabled: bool | None = None
    last_remind_time: str | None = None
    last_remind_content: str | None = None


class ReagentReminderConfigResponse(BaseModel):
    """`GET /config` — data is null until a config exists."""

    code: int = 200
    message: str = "success"
    data: ReagentReminderConfigData | None = None


class ReagentReminderSavedData(BaseModel):
    """The subset returned after saving — deliberately excludes the secret."""

    id: UUID
    feishu_app_id: str | None = None
    feishu_chat_id: str | None = None
    low_stock_threshold: int | None = None
    is_enabled: bool | None = None


class ReagentReminderSavedResponse(BaseModel):
    """`POST /config`"""

    code: int = 200
    message: str = "保存成功"
    data: ReagentReminderSavedData


class ReminderCheckData(BaseModel):
    """`/check` payload — varies by branch, so every field is optional.

    The service returns `data: null` for the early exits (no config, disabled,
    incomplete Feishu settings) and a count otherwise.
    """

    count: int | None = None
    total: int | None = None
    filtered: bool | None = None


class ReminderCheckResponse(BaseModel):
    """`POST /check`"""

    code: int = 200
    message: str = "success"
    data: ReminderCheckData | None = None


class LowStockItem(BaseModel):
    """One reagent below the threshold, with its reminder toggle state."""

    reagent_name: str
    count: int
    statuses: str | None = None
    units: str | None = None
    latest_arrival: str | None = None
    is_enabled: bool = True


class LowStockData(BaseModel):
    count: int
    items: list[LowStockItem]


class LowStockResponse(BaseModel):
    """`GET /low-stock`"""

    code: int = 200
    message: str = "success"
    data: LowStockData


class ItemReminderData(BaseModel):
    """`POST /item-reminder` returns no `data` key at all — hence the optional."""

    id: str | None = None
    reagent_name: str | None = None
    is_enabled: bool | None = None


class ItemReminderResponse(BaseModel):
    """`POST /item-reminder`"""

    code: int = 200
    message: str = "设置成功"
    data: ItemReminderData | None = None


class ItemReminderConfigResponse(BaseModel):
    """`GET /item-reminder/{reagent_name}` — defaults to enabled when unset."""

    code: int = 200
    message: str = "success"
    data: ItemReminderData
