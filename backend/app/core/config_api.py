"""Module settings API — CRUD for runtime configuration."""

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_model import ModuleSetting
from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import BadRequestException, DuplicateException, NotFoundException
from app.core.response import build_response
from app.core.secrets import decrypt_secret, encrypt_secret
from app.platform.identity.public_api import resolve_user_names
from app.shared.schemas import PaginationMeta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/module-settings", tags=["Module Settings"])

# 批量更新单次最多条数：布尔项批量启停的量级在 10~20 条，100 条足够且能挡住误用
_BATCH_LIMIT = 100

_BOOL_TRUE = {"true", "1", "yes", "on", "启用"}
_BOOL_FALSE = {"false", "0", "no", "off", "禁用"}


# ── Pydantic schemas ──────────────────────────────────────────


class ModuleSettingResponse(BaseModel):
    """Response schema for a module setting.

    ``value`` 对密钥类配置返回空串，真实值只以掩码形式出现在 ``value_masked``；
    前端编辑密钥项时留空即表示「保持不变」。
    """

    id: str
    module: str
    key: str
    label: str | None = None
    group_name: str | None = None
    value: str
    value_masked: str | None = None
    has_value: bool = True
    value_type: str
    value_hint: str | None = None
    description: str | None = None
    is_secret: bool = False
    updated_by_name: str | None = None
    manually_adjusted: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class ModuleSettingListApiResponse(BaseModel):
    """List envelope — concrete response model so OpenAPI types `data`."""

    code: int = 200
    message: str = "success"
    data: list[ModuleSettingResponse]
    meta: PaginationMeta | None = None


class ModuleSettingApiResponse(BaseModel):
    """Single-item envelope (404 returns data=None)."""

    code: int = 200
    message: str = "success"
    data: ModuleSettingResponse | None = None
    meta: PaginationMeta | None = None


class ModuleSettingUpdate(BaseModel):
    """Request schema for updating a setting value."""

    value: str = Field(..., description="New value (as string)")


class ModuleSettingCreate(BaseModel):
    """Request schema for creating a new setting."""

    module: str = Field(..., max_length=50, description="Module name")
    key: str = Field(..., max_length=100, description="Setting key")
    value: str = Field(..., description="Setting value")
    value_type: str = Field(default="string", pattern="^(string|int|bool|json)$")
    description: str | None = None
    label: str | None = Field(default=None, max_length=100, description="配置项中文名")
    group_name: str | None = Field(default=None, max_length=50, description="功能域分组名")
    is_secret: bool = Field(default=False, description="是否密钥类配置")
    value_hint: str | None = Field(default=None, max_length=200, description="取值提示")


class ModuleSettingBatchItem(BaseModel):
    """单条批量更新项。"""

    module: str = Field(..., max_length=50)
    key: str = Field(..., max_length=100)
    value: str


class ModuleSettingBatchUpdate(BaseModel):
    """批量更新请求（布尔项批量启停为主，也接受其他类型）。"""

    items: list[ModuleSettingBatchItem] = Field(..., min_length=1, max_length=_BATCH_LIMIT)


class ModuleSettingBatchFailure(BaseModel):
    """批量更新中失败的一条。"""

    module: str
    key: str
    label: str | None = None
    reason: str


class ModuleSettingBatchResult(BaseModel):
    """批量更新结果：成功的用 ``module:key`` 表示，失败项带原因。"""

    succeeded: list[str]
    failed: list[ModuleSettingBatchFailure]


class ModuleSettingBatchApiResponse(BaseModel):
    """Batch envelope."""

    code: int = 200
    message: str = "success"
    data: ModuleSettingBatchResult
    meta: PaginationMeta | None = None


# ── Helpers ───────────────────────────────────────────────────


def _mask_secret(value: str) -> str:
    """密钥掩码：长度 > 12 保留前 6 后 4，否则整体打码。"""
    if not value:
        return ""
    if len(value) > 12:
        return f"{value[:6]}****{value[-4:]}"
    return "******"


def _normalize_value(value_type: str, value: str) -> str:
    """按 value_type 校验并归一化配置值。

    校验失败抛 400（中文文案直接展示给用户），避免把 ``true`` 写成 ``abc``
    这类错误值落库、等到模块运行时才炸。
    """
    if value_type == "bool":
        raw = value.strip().lower()
        if raw in _BOOL_TRUE:
            return "true"
        if raw in _BOOL_FALSE:
            return "false"
        raise BadRequestException("布尔型配置只接受 启用 / 停用（true / false）")
    if value_type == "int":
        raw = value.strip()
        try:
            return str(int(raw))
        except (TypeError, ValueError) as exc:
            raise BadRequestException(f"该配置项要求整数，当前值「{value}」无法解析") from exc
    if value_type == "json":
        try:
            json.loads(value)
        except json.JSONDecodeError as exc:
            raise BadRequestException(f"JSON 格式不正确：第 {exc.lineno} 行第 {exc.colno} 列 {exc.msg}") from exc
        return value
    return value


def _stored_value(is_secret: bool, value_type: str, value: str) -> str:
    """校验后落库的字符串；密钥类配置必须加密存储。

    ``is_secret`` 只在写入侧加密，读取侧由 :func:`_plain_value` 统一解密，
    历史明文行（无 ``fernet:v1:`` 前缀）原样返回，无需一次性回填。
    """
    normalized = _normalize_value(value_type, value)
    return encrypt_secret(normalized) if is_secret else normalized


def _plain_value(setting: ModuleSetting) -> str:
    """取配置明文值；密钥类解密失败时降级为空，避免整个列表 500。"""
    if not setting.is_secret:
        return setting.value
    try:
        return decrypt_secret(setting.value)
    except RuntimeError:
        logger.warning(
            "module setting decrypt failed",
            extra={"biz_module": "core", "setting_key": setting.key},
        )
        return ""


def _to_response(setting: ModuleSetting, updated_by_name: str | None = None) -> ModuleSettingResponse:
    """ORM → 响应模型；密钥类只回掩码，不回明文。"""
    secret = bool(setting.is_secret)
    plain = _plain_value(setting)
    return ModuleSettingResponse(
        id=str(setting.id),
        module=setting.module,
        key=setting.key,
        label=setting.label,
        group_name=setting.group_name,
        value="" if secret else setting.value,
        value_masked=_mask_secret(plain) if secret else None,
        has_value=bool(plain),
        value_type=setting.value_type,
        value_hint=setting.value_hint,
        description=setting.description,
        is_secret=secret,
        updated_by_name=updated_by_name,
        manually_adjusted=setting.updated_by is not None,
        created_at=setting.created_at.isoformat() if setting.created_at else None,
        updated_at=setting.updated_at.isoformat() if setting.updated_at else None,
    )


async def _resolve_user_name(db: AsyncSession, user_id: Any) -> str | None:
    """回查修改人姓名（单条响应场景）。

    走 ``identity.public_api.resolve_user_names``，不直接引用 identity 的 ORM 模型。
    """
    if user_id is None:
        return None
    names = await resolve_user_names(db, [user_id])
    return names.get(user_id)


# ── Endpoints ─────────────────────────────────────────────────


@router.get("", response_model=ModuleSettingListApiResponse)
async def get(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("platform:module-setting:read")),
    module: str | None = Query(None, description="Filter by module name"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all module settings, optionally filtered by module.

    修改人姓名用一次批量回查带出，避免逐行回查（N+1）。
    """
    query = select(ModuleSetting).where(~ModuleSetting.is_deleted)

    if module:
        query = query.where(ModuleSetting.module == module)

    query = query.order_by(ModuleSetting.module, ModuleSetting.key)

    result = await db.execute(query)
    rows = list(result.scalars().all())
    user_names = await resolve_user_names(db, {row.updated_by for row in rows if row.updated_by})

    return build_response(
        data=[_to_response(row, user_names.get(row.updated_by) if row.updated_by else None) for row in rows]
    )


@router.put("/batch", response_model=ModuleSettingBatchApiResponse)
async def put_batch(
    data: ModuleSettingBatchUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("platform:module-setting:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """批量更新配置值（布尔项批量启停复用此接口）。

    逐条独立校验：成功项统一提交，失败项单独返回原因，互不影响。
    """
    started = time.monotonic()
    modules = {item.module for item in data.items}
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module.in_(sorted(modules)),
            ~ModuleSetting.is_deleted,
        )
    )
    existing = {(setting.module, setting.key): setting for setting in result.scalars().all()}

    succeeded: list[str] = []
    failed: list[ModuleSettingBatchFailure] = []

    for item in data.items:
        setting = existing.get((item.module, item.key))
        if setting is None:
            failed.append(ModuleSettingBatchFailure(module=item.module, key=item.key, reason="配置项不存在"))
            continue
        if setting.is_secret and not item.value.strip():
            failed.append(
                ModuleSettingBatchFailure(
                    module=item.module,
                    key=item.key,
                    label=setting.label,
                    reason="密钥类配置不能为空",
                )
            )
            continue
        try:
            setting.value = _stored_value(setting.is_secret, setting.value_type, item.value)
        except BadRequestException as exc:
            failed.append(
                ModuleSettingBatchFailure(
                    module=item.module,
                    key=item.key,
                    label=setting.label,
                    reason=exc.message,
                )
            )
            continue
        setting.updated_by = current_user.id
        succeeded.append(f"{item.module}:{item.key}")

    if succeeded:
        await db.commit()

    logger.info(
        "module settings batch updated",
        extra={
            "biz_module": "core",
            "succeeded_count": len(succeeded),
            "failed_count": len(failed),
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        },
    )

    return build_response(data=ModuleSettingBatchResult(succeeded=succeeded, failed=failed))


@router.get("/{module}/{key}", response_model=ModuleSettingApiResponse)
async def get_one(
    module: str,
    key: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("platform:module-setting:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific setting by module and key."""
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == module,
            ModuleSetting.key == key,
            ~ModuleSetting.is_deleted,
        )
    )
    setting = result.scalar_one_or_none()

    if not setting:
        raise NotFoundException("配置项")

    return build_response(data=_to_response(setting, await _resolve_user_name(db, setting.updated_by)))


@router.put("/{module}/{key}", response_model=ModuleSettingApiResponse)
async def put(
    module: str,
    key: str,
    data: ModuleSettingUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("platform:module-setting:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update a setting value.

    - 按 ``value_type`` 做服务端校验，非法值直接 400；
    - 密钥类配置传空串表示「保持不变」（界面不回填明文，无法区分「清空」）。
    """
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == module,
            ModuleSetting.key == key,
            ~ModuleSetting.is_deleted,
        )
    )
    setting = result.scalar_one_or_none()

    if not setting:
        raise NotFoundException("配置项")

    if setting.is_secret and not data.value.strip():
        # 密钥项留空 = 不修改，避免前端因掩码回填而误清空凭证
        return build_response(data=_to_response(setting, current_user.name))

    setting.value = _stored_value(setting.is_secret, setting.value_type, data.value)
    setting.updated_by = current_user.id

    await db.commit()
    await db.refresh(setting)

    return build_response(data=_to_response(setting, current_user.name))


@router.post("", response_model=ModuleSettingApiResponse, status_code=201)
async def post(
    data: ModuleSettingCreate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("platform:module-setting:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new module setting."""
    # Check for duplicate
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == data.module,
            ModuleSetting.key == data.key,
            ~ModuleSetting.is_deleted,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise DuplicateException("配置项", f"{data.module}:{data.key}")

    setting = ModuleSetting(
        module=data.module,
        key=data.key,
        value=_stored_value(data.is_secret, data.value_type, data.value),
        value_type=data.value_type,
        description=data.description,
        label=data.label,
        group_name=data.group_name,
        is_secret=data.is_secret,
        value_hint=data.value_hint,
        created_by=current_user.id,
        updated_by=current_user.id,
    )

    db.add(setting)
    await db.commit()
    await db.refresh(setting)

    return build_response(data=_to_response(setting, current_user.name))


@router.delete("/{module}/{key}", response_model=ModuleSettingApiResponse)
async def delete(
    module: str,
    key: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("platform:module-setting:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Soft delete a module setting."""
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == module,
            ModuleSetting.key == key,
            ~ModuleSetting.is_deleted,
        )
    )
    setting = result.scalar_one_or_none()

    if not setting:
        raise NotFoundException("配置项")

    setting.is_deleted = True
    setting.updated_by = current_user.id

    await db.commit()
    return build_response(message="Setting deleted")
