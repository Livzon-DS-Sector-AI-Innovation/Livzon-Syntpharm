import json
import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

UserStatus = Literal["active", "disabled"]
AuthSource = Literal["local", "feishu"]

# 中国标准时间（UTC+8）：登录记录属审计信息，统一按北京时间展示
CST = timezone(timedelta(hours=8))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: "UserResponse | None" = None


class LocalLoginApiResponse(BaseModel):
    """本地账号密码登录响应（完整信封）。"""

    code: int = 200
    message: str = "success"
    data: TokenResponse


class LocalLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class SSOCallbackResult(BaseModel):
    token: str
    redirect_url: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    username: str | None = None
    auth_source: AuthSource = "feishu"
    en_name: str | None = None
    email: str | None = None
    enterprise_email: str | None = None
    mobile: str | None = None
    avatar_url: str | None = None
    avatar_thumb: str | None = None
    avatar_middle: str | None = None
    avatar_big: str | None = None
    employee_no: str | None = None
    department: str | None = None
    position: str | None = None
    feishu_user_id: str | None = None
    feishu_open_id: str | None = None
    feishu_union_id: str | None = None
    tenant_key: str | None = None
    # 强制改密标记：登录后前端据此把用户挡在 /change-password（管理员重置密码后为 true）
    must_change_password: bool = False

    model_config = {"from_attributes": True}


class UserManagementItem(UserResponse):
    status: str = "active"  # 用户状态（active / disabled）；用户管理列表的「状态」列依赖该字段
    last_login_at: str | None = None
    password_updated_at: str | None = None  # 密码最后修改时间（管理员重置后更新）
    created_at: str | None = None  # 账号创建时间（用户管理列表的「创建时间」列）
    # 有效角色名列表（来自权限管理的授权，非 User.role 之类的历史字段）
    roles: list[str] = Field(default_factory=list)
    # 是否超级管理员：列表多选批量操作时前端据此禁用复选框（后端仍会逐条校验）
    is_superuser: bool = False

    @field_validator("last_login_at", "password_updated_at", "created_at", mode="before")
    @classmethod
    def datetime_to_str(cls, v: object) -> str | None:
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()  # type: ignore[no-any-return]
        return str(v)


class UserManagementListResponse(BaseModel):
    items: list[UserManagementItem]
    total: int
    offset: int
    limit: int


class UserBatchStatusRequest(BaseModel):
    """批量启用 / 禁用账号。"""

    user_ids: list[UUID] = Field(..., min_length=1, max_length=100, description="单次最多 100 个账号")
    status: UserStatus


class UserBatchFailure(BaseModel):
    id: UUID
    username: str | None = None
    reason: str


class UserBatchStatusData(BaseModel):
    succeeded: list[UUID] = Field(default_factory=list)
    failed: list[UserBatchFailure] = Field(default_factory=list)


class UserBatchStatusApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserBatchStatusData


# 登录用户名字符集：字母开头 + 字母数字。
# 要求字母开头有两个原因：①登录时账号会与手机号 / 工号一起参与匹配，纯数字账号会产生歧义；
# ②与飞书首登自动分配的用户名（如 YTH000001）保持同一种风格。
USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,63}$")
USERNAME_RULE_MESSAGE = "账号只能由字母和数字组成，且必须以字母开头（2-64 位）"


class LocalUserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    # 留空 = 由后端自动生成随机初始密码（一次性返回明文，仅本次可见）
    password: str | None = Field(
        None,
        min_length=6,
        max_length=255,
        description="初始密码；留空则自动生成，明文只在创建响应里返回一次",
    )
    name: str = Field(..., min_length=1, max_length=100)
    email: str | None = Field(None, max_length=255)
    mobile: str | None = Field(None, max_length=32)
    employee_no: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=200)
    position: str | None = Field(None, max_length=200)
    status: UserStatus = "active"

    @field_validator("username", mode="before")
    @classmethod
    def validate_username_charset(cls, v: object) -> str:
        """新建账号拒绝中文等非 ASCII 用户名（历史账号不受影响，更新接口不做该校验）。"""
        if not isinstance(v, str):
            raise ValueError(USERNAME_RULE_MESSAGE)
        value = v.strip()
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError(USERNAME_RULE_MESSAGE)
        return value


class UserCreateData(UserManagementItem):
    """新建账号响应：额外带回一次性初始密码（仅自动生成时有值，不落库）。"""

    initial_password: str | None = None


class UserCreateApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserCreateData


class UserManagementUpdate(BaseModel):
    username: str | None = Field(None, min_length=2, max_length=64, description="登录账号（创建后不可修改）")
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, max_length=255)
    mobile: str | None = Field(None, max_length=32)
    employee_no: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=200)
    position: str | None = Field(None, max_length=200)
    status: UserStatus | None = None


class PasswordResetRequest(BaseModel):
    """管理员重置密码。

    `password` 留空 = 随机生成：生成的明文密码只在响应里返回一次（一次性展示），
    数据库仍只存哈希，之后无法再次查看。两种情况都会把账号标记为「首登需改密」。
    """

    password: str | None = Field(None, min_length=6, max_length=255)


class PasswordResetData(BaseModel):
    message: str
    # 仅「随机生成」时返回，供管理员当场抄给用户；不落库
    password: str | None = None


class PasswordResetApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: PasswordResetData


class UserDeleteData(BaseModel):
    """删除账号结果（软删除，账号名继续被占用）。"""

    id: UUID
    username: str | None = None
    revoked_grants: int = 0
    revoked_sessions: int = 0


class UserDeleteApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserDeleteData


class ChangePasswordRequest(BaseModel):
    """当前登录用户自助改密。"""

    old_password: str = Field(..., min_length=1, max_length=255)
    new_password: str = Field(..., min_length=6, max_length=255)


class ChangePasswordData(BaseModel):
    message: str


class ChangePasswordApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: ChangePasswordData


class FeishuBindRequest(BaseModel):
    """绑定飞书用户：把库里已存在的飞书用户记录合并进目标账号。"""

    source_user_id: UUID = Field(..., description="飞书用户记录的 ID（auth_source=feishu）")


# ── Department ──────────────────────────────────────────────────────


class DepartmentResponse(BaseModel):
    id: UUID
    feishu_department_id: str
    name: str
    parent_feishu_department_id: str | None = None
    leader_user_id: str | None = None
    member_count: int | None = None
    status_is_deleted: bool | None = None
    path: str | None = None
    order: int | None = None

    @field_validator("path", mode="before")
    @classmethod
    def path_to_str(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, list | dict):
            return json.dumps(v, ensure_ascii=False)
        return str(v)

    model_config = {"from_attributes": True}


class DepartmentTreeNode(BaseModel):
    """组织架构树节点（含子部门）"""

    id: UUID
    feishu_department_id: str
    name: str
    member_count: int | None = None
    leader_user_id: str | None = None
    order: int | None = None
    children: list["DepartmentTreeNode"] = []

    model_config = {"from_attributes": True}


# ── Personnel ───────────────────────────────────────────────────────


class PersonnelItem(BaseModel):
    """人员列表项"""

    id: UUID
    name: str
    # 登录账号：选人下拉用「姓名（账号）」展示，重名时可区分
    username: str | None = None
    en_name: str | None = None
    employee_no: str | None = None
    email: str | None = None
    enterprise_email: str | None = None
    mobile: str | None = None
    department: str | None = None
    position: str | None = None
    feishu_user_id: str | None = None
    feishu_open_id: str | None = None
    feishu_union_id: str | None = None
    avatar_url: str | None = None
    avatar_thumb: str | None = None
    avatar_middle: str | None = None
    avatar_big: str | None = None
    tenant_key: str | None = None
    feishu_department_ids: list[str] | None = None

    @field_validator("feishu_department_ids", mode="before")
    @classmethod
    def parse_dept_ids(cls, v: object) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)  # type: ignore[no-any-return]
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    model_config = {"from_attributes": True}


class PersonnelListResponse(BaseModel):
    """人员分页列表"""

    items: list[PersonnelItem]
    total: int
    offset: int
    limit: int


# ── Login Log ──────────────────────────────────────────────────────


class LoginLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None = None
    user_name: str | None = None
    login_type: str
    status: str
    ip_address: str | None = None
    user_agent: str | None = None
    error_message: str | None = None
    created_at: str

    model_config = {"from_attributes": True}

    @field_validator("created_at", mode="before")
    @classmethod
    def format_created_at(cls, v: object) -> str:
        """统一转成北京时间字符串。

        库里存的是 UTC（`timestamptz`），直接 `strftime` 会得到 UTC 时间、
        页面上比北京时间少 8 小时（曾导致「刚登录但记录里看不到」的误判）。
        """
        if isinstance(v, datetime):
            aware = v if v.tzinfo else v.replace(tzinfo=UTC)
            return aware.astimezone(CST).strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(v, "strftime"):
            return v.strftime("%Y-%m-%d %H:%M:%S")  # type: ignore[no-any-return]
        return str(v)


class LoginLogListResponse(BaseModel):
    items: list[LoginLogResponse]
    total: int
    page: int
    page_size: int


# ── Livzon Assistant Feishu Config ─────────────────────────────────


class FeishuConfigUpsert(BaseModel):
    config_name: str = Field(
        default="Livzon 助手飞书设置",
        min_length=1,
        max_length=128,
        description="配置名称，仅用于 Livzon 助手",
    )
    app_id: str = Field(..., min_length=1, max_length=128)
    app_secret: str | None = Field(default=None, max_length=500)
    card_callback_verification_token: str | None = Field(default=None, max_length=512)
    card_callback_encrypt_key: str | None = Field(default=None, max_length=500)
    sync_root_department_id: str | None = Field(default=None, max_length=128)
    sync_member_department_id: str | None = Field(default=None, max_length=128)
    is_active: bool = True

    @field_validator(
        "config_name",
        "app_id",
        "app_secret",
        "card_callback_verification_token",
        "card_callback_encrypt_key",
        "sync_root_department_id",
        "sync_member_department_id",
        mode="before",
    )
    @classmethod
    def clean_text(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class FeishuConfigResponse(BaseModel):
    id: UUID | None = None
    config_name: str = "Livzon 助手飞书设置"
    app_id: str = ""
    app_secret_configured: bool = False
    app_secret_masked: str = ""
    card_callback_verification_token_configured: bool = False
    card_callback_verification_token_masked: str = ""
    card_callback_encrypt_key_configured: bool = False
    card_callback_encrypt_key_masked: str = ""
    card_callback_url: str = "/api/v1/identity/feishu/card-callback"
    sync_root_department_id: str | None = None
    sync_member_department_id: str | None = None
    is_active: bool = True
    last_sync_status: str | None = None
    last_sync_message: str | None = None
    last_synced_at: str | None = None
    last_diagnostic_status: str | None = None
    last_diagnostic_message: str | None = None
    last_diagnostic_result: str | None = None
    last_diagnosed_at: str | None = None

    @field_validator("last_synced_at", "last_diagnosed_at", mode="before")
    @classmethod
    def datetime_to_str(cls, value: object) -> str | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()  # type: ignore[no-any-return]
        return str(value)


class FeishuDiagnosticStep(BaseModel):
    name: str
    status: Literal["ok", "warning", "error"]
    message: str
    suggestion: str | None = None
    code: int | None = None


class FeishuDiagnosticResult(BaseModel):
    status: Literal["ok", "warning", "error"]
    message: str
    steps: list[FeishuDiagnosticStep]
    department_count: int = 0
    sample_user_count: int = 0


class FeishuConfigApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: FeishuConfigResponse


class FeishuDiagnosticApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: FeishuDiagnosticResult


class FeishuCardCallbackResponse(BaseModel):
    toast: dict[str, Any] | None = None
    card: dict[str, Any] | None = None
    challenge: str | None = None


# ── API 响应信封（具体 response_model，替换 JSONResponse/Any） ──


class CurrentUserApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserResponse


class UserManagementApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserManagementItem


class UserManagementListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserManagementListResponse


class UserBindFeishuData(UserManagementItem):
    """绑定飞书结果：UserManagementItem + 授权迁移计数。"""

    bind_result: dict[str, int] | None = None


class UserBindFeishuApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserBindFeishuData


class UserUnbindFeishuData(UserManagementItem):
    """解绑飞书结果：UserManagementItem + 是否因解绑而软删账号。"""

    account_deleted: bool = False


class UserUnbindFeishuApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: UserUnbindFeishuData


class SessionItem(BaseModel):
    """在线会话条目（Redis 中存储的会话信息）。"""

    jti: str
    user_id: str | None = None
    name: str | None = None
    username: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: str | None = None


class SessionListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[SessionItem]


class SessionRevokeData(BaseModel):
    """吊销会话结果：单条为布尔，批量为用户会话数。"""

    revoked: bool | int


class SessionRevokeApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: SessionRevokeData


class SyncDepartmentsTriggerData(BaseModel):
    message: str
    root_dept_id: str


class SyncDepartmentsTriggerApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: SyncDepartmentsTriggerData


class SyncMembersTriggerData(BaseModel):
    message: str
    target_dept_id: str


class SyncMembersTriggerApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: SyncMembersTriggerData


class SyncAllTriggerData(BaseModel):
    status: str
    message: str


class SyncAllTriggerApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: SyncAllTriggerData
