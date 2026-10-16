import json
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
    # 有效角色名列表（来自权限管理的授权，非 User.role 之类的历史字段）
    roles: list[str] = Field(default_factory=list)

    @field_validator("last_login_at", "password_updated_at", mode="before")
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


class LocalUserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=255)
    name: str = Field(..., min_length=1, max_length=100)
    email: str | None = Field(None, max_length=255)
    mobile: str | None = Field(None, max_length=32)
    employee_no: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=200)
    position: str | None = Field(None, max_length=200)
    status: UserStatus = "active"


class UserManagementUpdate(BaseModel):
    username: str | None = Field(None, min_length=2, max_length=64, description="登录用户名（创建后不可修改）")
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
