"""菜单栏管理 API 模型（完整信封，见 AGENTS「API 规范」）。

配置语义（与前端 `frontend/src/lib/menu-config.ts` 的菜单结构对齐）：
- `items`：**内置**菜单项的覆盖配置（未设置的字段 = 按前端代码默认，保持既有行为）；
- `custom`：管理员**自定义新增**的菜单项（父级为 null 时是模块级，即顶部一个 Tab）。
"""

from pydantic import BaseModel, Field


class MenuItemOverride(BaseModel):
    """内置菜单项的覆盖配置。"""

    label: str | None = Field(
        None, max_length=64, description="菜单显示名；None/空 = 按代码默认（菜单管理里可改）"
    )
    visible: bool | None = Field(None, description="是否显示；None = 按代码默认（显示）")
    sort: int | None = Field(None, description="排列权重，数字小排前面；None = 按代码顺序")
    perms: list[str] | None = Field(
        None,
        description="需要的权限码（任一满足即可）；None = 按代码默认规则；[] = 不限制",
    )


class CustomMenuItem(BaseModel):
    """管理员自定义新增的菜单项。"""

    id: str = Field(..., min_length=1, max_length=64, description="自定义项 ID（前端生成）")
    parent: str | None = Field(None, description="父菜单 key；None = 模块级（顶部一个 Tab）")
    title: str = Field(..., min_length=1, max_length=64, description="菜单名称")
    path: str = Field(..., min_length=1, max_length=512, description="跳转路径（/xxx 或 http(s)://）")
    icon: str = Field("link", max_length=64, description="图标名（取前端可用图标集合）")
    sort: int = Field(100, description="排列权重，数字小排前面")
    perms: list[str] = Field(default_factory=list, description="需要的权限码；空 = 不限制")
    visible: bool = True


class MenuConfigData(BaseModel):
    items: dict[str, MenuItemOverride] = Field(default_factory=dict)
    custom: list[CustomMenuItem] = Field(default_factory=list)
    updated_at: str | None = None


class MenuConfigResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: MenuConfigData


class MenuConfigSaveRequest(BaseModel):
    items: dict[str, MenuItemOverride] = Field(default_factory=dict)
    custom: list[CustomMenuItem] = Field(default_factory=list)


class MenuConfigSaveResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: MenuConfigData
