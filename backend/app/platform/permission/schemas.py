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
    role_type: str = "job"
    module_code: str | None = None
    description: str | None = None
    is_builtin: bool = False
    is_superuser: bool = False
    status: str = "active"
    # 内置角色是否已被人工接管（true 时启动同步不再改动其权限）
    sync_locked: bool = False


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
    code: str | None = Field(
        None,
        min_length=2,
        max_length=128,
        description="留空时由后端自动生成（模块角色为 {module}:role-NNN，平台角色为 platform:role-NNN）",
    )
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
    # 展示用中文派生字段：数据来自注册表；库里存在注册表已退役的码时为 None，前端回退英文原值
    module_label: str | None = Field(None, description="模块中文名（注册表派生）")
    resource_label: str | None = Field(None, description="资源中文名（注册表派生）")
    action_label: str | None = Field(None, description="动作中文短词（注册表派生）")


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
    # 授予时间（授权列表展示，取自 user_role_grants.created_at）
    created_at: str | None = None
    # 冗余展示字段（join 查询填充）
    role_code: str | None = None
    role_name: str | None = None
    user_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    # 部门 / 职务实时取自 HR 员工档案（identity.users 自 #219 起不再维护这两个字段）；
    # 无档案的账号（本地账号等）为空，前端显示「—」。
    department_name: str | None = None
    department_path_text: str | None = None
    position_name: str | None = None


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


# ── 授权数据范围部门选项（hr.departments.code + name）───────────────


class DepartmentOption(BaseModel):
    code: str
    name: str


class DepartmentOptionListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[DepartmentOption]


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


class PermissionApiBindingItem(BaseModel):
    """单个权限码绑定的接口（来源为 registry 常量，无 DB 主键）。"""

    method: str = Field(..., description="HTTP 方法，如 GET / POST")
    route_template: str = Field(..., description="接口路由模板，路径参数以 {name} 占位")
    scope_required: bool = Field(False, description="该接口是否要求数据范围")


class PermissionApiBindingListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[PermissionApiBindingItem] = Field(..., description="该权限码绑定的接口清单")


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


# ── 批量操作（角色 / 授权）────────────────────────────────────────


class IdsBatchRequest(BaseModel):
    """按 ID 批量操作；单次上限 100。"""

    ids: list[UUID] = Field(..., min_length=1, max_length=100)


class StatusBatchRequest(IdsBatchRequest):
    status: str = Field(..., pattern="^(active|disabled)$")


class GrantBatchCreate(BaseModel):
    """批量授权：多用户 × 多角色，统一套用同一个数据范围。

    `user_ids` 可以是统一人员选择器返回的 `hr.employee_profiles.id`，也可以是
    `identity.users.id`；端点内部统一经 `resolve_person_user_id` 转换。
    """

    user_ids: list[UUID] = Field(..., min_length=1, max_length=100, description="单次最多 100 个用户")
    role_ids: list[UUID] = Field(..., min_length=1, max_length=20, description="单次最多 20 个角色")
    scope_type: str = Field(default="all", pattern="^(self|department|department_and_children|all)$")
    scope_dept_codes: list[str] | None = None


class BatchFailure(BaseModel):
    key: str
    label: str | None = None
    reason: str


class BatchResultData(BaseModel):
    succeeded: list[str] = Field(default_factory=list)
    failed: list[BatchFailure] = Field(default_factory=list)


class BatchResultApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: BatchResultData


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


# ── 模块负责人 / 模块管理员（系统管理员侧）───────────────────────────


class ModuleAdminUser(BaseModel):
    """某个模块下的一名负责人/管理人。"""

    grant_id: UUID
    user_id: UUID
    name: str | None = None
    username: str | None = None
    role_code: str
    role_type: str


class ModuleAdminGroup(BaseModel):
    """一个模块的负责人与管理人清单。"""

    module_code: str
    module_name: str
    heads: list[ModuleAdminUser] = Field(default_factory=list)
    managers: list[ModuleAdminUser] = Field(default_factory=list)


class ModuleAdminListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[ModuleAdminGroup]


class ModuleAdminAssignRequest(BaseModel):
    module_code: str = Field(..., max_length=64)
    role_type: str = Field(
        ...,
        pattern="^owner$",
        description="owner=模块负责人（本入口只指派负责人；模块代表由负责人在模块配置页指派）",
    )
    user_id: UUID = Field(..., description="identity.users.id 或 hr.employee_profiles.id")


class UserAccessItem(BaseModel):
    """某用户的一条模块权限（离职/调岗收权兜底视图）。"""

    grant_id: UUID
    role_id: UUID
    role_code: str
    role_name: str
    role_type: str
    module_code: str | None = None
    status: str


class UserAccessData(BaseModel):
    user_id: UUID
    name: str | None = None
    username: str | None = None
    is_superuser: bool = False
    items: list[UserAccessItem] = Field(default_factory=list)


class UserAccessResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserAccessData


class UserAccessDisableData(BaseModel):
    disabled: int = 0


class UserAccessDisableResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserAccessDisableData
