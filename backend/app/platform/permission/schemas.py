"""权限模块请求 / 响应模型。

响应模型按 AGENTS.md 要求描述完整响应体（code / message / data）。
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── 角色 ──────────────────────────────────────────────────────────


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    category: str
    module_code: str | None = None
    description: str | None = None
    is_builtin: bool = False
    is_superuser: bool = False
    status: str = "active"


class RoleDetailResponse(RoleResponse):
    permission_codes: list[str] = Field(default_factory=list)


class RoleListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[RoleDetailResponse]


class RoleDetailApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: RoleDetailResponse


class RoleCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=128)
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(default="module", pattern="^(platform|module)$")
    module_code: str | None = Field(None, max_length=64)
    description: str | None = Field(None, max_length=500)
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    permission_codes: list[str] | None = None
    status: str | None = Field(None, pattern="^(active|disabled)$")


# ── 权限目录 ──────────────────────────────────────────────────────


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    module: str
    resource: str
    action: str
    description: str | None = None
    status: str = "active"
    is_builtin: bool = True


class PermissionListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[PermissionResponse]


# ── 授权 ──────────────────────────────────────────────────────────


class GrantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    role_id: UUID
    scope_type: str
    scope_dept_codes: list[str] | None = None
    status: str = "active"
    granted_by: UUID | None = None
    version: int = 1
    # 冗余展示字段（join 查询填充）
    role_code: str | None = None
    role_name: str | None = None
    user_name: str | None = None


class GrantListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[GrantResponse]


class GrantDetailApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: GrantResponse


class GrantCreate(BaseModel):
    user_id: UUID
    role_id: UUID
    scope_type: str = Field(default="all", pattern="^(self|department|department_and_children|all)$")
    scope_dept_codes: list[str] | None = None


class GrantUpdate(BaseModel):
    scope_type: str | None = Field(None, pattern="^(self|department|department_and_children|all)$")
    scope_dept_codes: list[str] | None = None
    status: str | None = Field(None, pattern="^(active|disabled)$")


# ── 接口绑定登记簿 ────────────────────────────────────────────────


class ApiBindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    permission_code: str
    method: str
    route_template: str
    scope_required: bool = False
    status: str = "active"


class ApiBindingListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[ApiBindingResponse]


# ── 当前用户权限 ──────────────────────────────────────────────────


class MyPermissionsData(BaseModel):
    permissions: list[str] = Field(default_factory=list)
    is_superuser: bool = False


class MyPermissionsResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: MyPermissionsData


# ── 通用消息 ──────────────────────────────────────────────────────


class MessageApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: None = None


# ── 权限目录树（角色管理界面渲染用）───────────────────────────────


class PermissionTreeNode(BaseModel):
    key: str = Field(..., description="树节点唯一键（前端 Tree 用）")
    title: str = Field(..., description="显示名")
    type: str = Field(..., description="module / resource / permission")
    code: str | None = Field(None, description="模块编码或权限码")
    kind: str | None = Field(None, description="模块节点类别：platform / business")
    status: str | None = Field(None, description="权限叶子状态：active / deprecated")
    description: str | None = Field(None, description="权限说明")
    binding_count: int = Field(0, description="该权限码绑定的接口数量（仅叶子）")
    disabled: bool = Field(False, description="是否置灰（如尚未接入权限码的模块）")
    children: list["PermissionTreeNode"] = Field(default_factory=list)


class PermissionTreeData(BaseModel):
    tree: list[PermissionTreeNode]
    total_permissions: int
    total_modules: int


class PermissionTreeResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: PermissionTreeData
