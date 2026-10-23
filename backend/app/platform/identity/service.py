"""Authentication service — handles OAuth callback, JWT generation, user upsert."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from typing import Any
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.secrets import decrypt_secret, encrypt_secret, mask_secret
from app.platform.audit.models import AuditLog
from app.platform.identity.models import FeishuCardAction, FeishuConfig, User
from app.platform.identity.repository import (
    FeishuCardActionRepository,
    FeishuConfigRepository,
    UserRepository,
)
from app.platform.identity.schemas import (
    FeishuConfigResponse,
    FeishuConfigUpsert,
    FeishuDiagnosticResult,
    FeishuDiagnosticStep,
)
from app.platform.integrations.feishu.oauth import FeishuOAuthClient
from app.shared.config_reader import get_module_setting

logger = logging.getLogger(__name__)

_repo = UserRepository()
_feishu_config_repo = FeishuConfigRepository()
_feishu_card_action_repo = FeishuCardActionRepository()
_PASSWORD_ITERATIONS = 260_000
SYSTEM_ADMIN_USERNAME = "system_admin"
SYSTEM_ADMIN_NAME = "系统管理员"
DEFAULT_FEISHU_CONFIG_NAME = "Livzon 助手飞书设置"
ALLOWED_CARD_ACTIONS = {
    "start_processing": "开始处理",
    "mark_done": "标记完成",
    "reject": "驳回",
    "acknowledge": "已知悉",
}


def _secret_runtime_error(exc: RuntimeError) -> HTTPException:
    return HTTPException(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        (f"Livzon 助手飞书密钥加解密失败：{exc}。请检查后端 ENCRYPTION_KEY 配置是否与保存配置时一致。"),
    )


def hash_password(password: str) -> str:
    """Hash a local-account password using PBKDF2-SHA256."""
    salt = secrets.token_bytes(16)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${_PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
    except (ValueError, TypeError):
        return False
    return compare_digest(expected, digest_hex)


# ── 本地账号凭据：默认用户名与随机密码 ──────────────────────────────
# 飞书首次登录时为账号补齐本地用户名（`{前缀}{6 位自增号}`），但不自动生成密码：
# 密码由管理员在「用户管理」按需随机生成并**一次性展示**，库里只存哈希。
# 若在这里生成密码，既没有人在场查看，也等于凭空多出一条无人知晓的登录凭据。

DEFAULT_USERNAME_PREFIX = "YTH"
USERNAME_PREFIX_SETTING_KEY = "USERNAME_PREFIX"

# 随机密码字符集：剔除 0/O、1/l/I 等易混字符，避免管理员抄错
PASSWORD_ALPHABET = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
DEFAULT_PASSWORD_LENGTH = 12


def generate_random_password(length: int = DEFAULT_PASSWORD_LENGTH) -> str:
    """生成随机初始密码（只用于一次性展示，不落库明文）。"""
    if length < 6:
        length = DEFAULT_PASSWORD_LENGTH
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


MIN_PASSWORD_LENGTH = 8


def validate_password_strength(password: str) -> str | None:
    """校验密码复杂度：≥8 位且同时含字母与数字。合规返回 None，否则返回错误文案。"""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"密码长度至少 {MIN_PASSWORD_LENGTH} 位"
    if not any(c.isalpha() for c in password):
        return "密码需包含字母"
    if not any(c.isdigit() for c in password):
        return "密码需包含数字"
    return None


async def resolve_username_prefix() -> str:
    """用户名前缀：运行时配置 `identity.USERNAME_PREFIX` 优先，缺省 YTH。"""
    raw = await get_module_setting("identity", USERNAME_PREFIX_SETTING_KEY, DEFAULT_USERNAME_PREFIX)
    # 只保留 ASCII 字母数字：中文前缀会生成中文用户名，与新建账号的字符集规则冲突
    cleaned = "".join(ch for ch in raw.strip().upper() if ch.isascii() and ch.isalnum())[:8]
    return cleaned or DEFAULT_USERNAME_PREFIX


async def allocate_default_username(db: AsyncSession) -> str:
    """分配默认用户名，如 `YTH000001`。"""
    return await _repo.allocate_username(db, prefix=await resolve_username_prefix())


async def ensure_default_username(db: AsyncSession, user: User) -> str:
    """补齐本地用户名并返回。

    「先同步、后登录」的账号（`sync_members` 走 `create` 但只写飞书字段）与历史账号
    都在这里补齐 —— 只在建号时分配的话，这些账号永远无法用账号密码登录。
    """
    if not user.username:
        user.username = await allocate_default_username(db)
    return user.username


def _split_identifiers(raw: str) -> set[str]:
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _matches_admin_whitelist(user: User, raw_identifiers: str) -> bool:
    identifiers = _split_identifiers(raw_identifiers)
    if not identifiers:
        return False
    candidates = {
        user.username,
        user.feishu_open_id,
        user.feishu_user_id,
        user.email,
        user.enterprise_email,
        user.mobile,
        user.employee_no,
    }
    return any(value and value.lower() in identifiers for value in candidates)


def _empty_feishu_config_response() -> FeishuConfigResponse:
    return FeishuConfigResponse(
        config_name=DEFAULT_FEISHU_CONFIG_NAME,
        app_id="",
        app_secret_configured=False,
        app_secret_masked="",
        card_callback_verification_token_configured=False,
        card_callback_verification_token_masked="",
        card_callback_encrypt_key_configured=False,
        card_callback_encrypt_key_masked="",
        is_active=True,
    )


def _feishu_config_to_response(config: FeishuConfig | None) -> FeishuConfigResponse:
    if config is None:
        return _empty_feishu_config_response()
    secret = ""
    if config.encrypted_app_secret:
        try:
            secret = decrypt_secret(config.encrypted_app_secret)
        except RuntimeError:
            secret = ""
    encrypt_key = ""
    if config.encrypted_card_callback_encrypt_key:
        try:
            encrypt_key = decrypt_secret(config.encrypted_card_callback_encrypt_key)
        except RuntimeError:
            encrypt_key = ""
    return FeishuConfigResponse(
        id=config.id,
        config_name=config.config_name,
        app_id=config.app_id,
        app_secret_configured=bool(config.encrypted_app_secret),
        app_secret_masked=mask_secret(secret),
        card_callback_verification_token_configured=bool(config.card_callback_verification_token),
        card_callback_verification_token_masked=mask_secret(config.card_callback_verification_token or ""),
        card_callback_encrypt_key_configured=bool(config.encrypted_card_callback_encrypt_key),
        card_callback_encrypt_key_masked=mask_secret(encrypt_key),
        sync_root_department_id=config.sync_root_department_id,
        sync_member_department_id=config.sync_member_department_id,
        is_active=config.is_active,
        last_sync_status=config.last_sync_status,
        last_sync_message=config.last_sync_message,
        last_synced_at=config.last_synced_at,
        last_diagnostic_status=config.last_diagnostic_status,
        last_diagnostic_message=config.last_diagnostic_message,
        last_diagnostic_result=config.last_diagnostic_result,
        last_diagnosed_at=config.last_diagnosed_at,
    )


async def get_livzon_feishu_config_response(db: AsyncSession) -> FeishuConfigResponse:
    config = await _feishu_config_repo.get_latest(db)
    return _feishu_config_to_response(config)


async def save_livzon_feishu_config(db: AsyncSession, payload: FeishuConfigUpsert) -> FeishuConfigResponse:
    existing = await _feishu_config_repo.get_latest(db)
    target_name = payload.config_name or DEFAULT_FEISHU_CONFIG_NAME
    if existing is None:
        existing = await _feishu_config_repo.get_by_name_including_deleted(
            db,
            target_name,
        )
    try:
        encrypted_secret = (
            encrypt_secret(payload.app_secret)
            if payload.app_secret
            else existing.encrypted_app_secret
            if existing
            else ""
        )
        encrypted_callback_key = (
            encrypt_secret(payload.card_callback_encrypt_key)
            if payload.card_callback_encrypt_key
            else existing.encrypted_card_callback_encrypt_key
            if existing
            else None
        )
    except RuntimeError as exc:
        raise _secret_runtime_error(exc) from exc
    callback_token = (
        payload.card_callback_verification_token
        if payload.card_callback_verification_token is not None
        else existing.card_callback_verification_token
        if existing
        else None
    )
    if not encrypted_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请输入 App Secret")

    if existing:
        existing.config_name = target_name
        existing.app_id = payload.app_id
        existing.encrypted_app_secret = encrypted_secret
        existing.card_callback_verification_token = callback_token
        existing.encrypted_card_callback_encrypt_key = encrypted_callback_key
        existing.sync_root_department_id = payload.sync_root_department_id
        existing.sync_member_department_id = payload.sync_member_department_id
        existing.is_active = payload.is_active
        existing.is_deleted = False
        await db.flush()
        return _feishu_config_to_response(existing)

    config = FeishuConfig(
        config_name=target_name,
        app_id=payload.app_id,
        encrypted_app_secret=encrypted_secret,
        card_callback_verification_token=callback_token,
        encrypted_card_callback_encrypt_key=encrypted_callback_key,
        sync_root_department_id=payload.sync_root_department_id,
        sync_member_department_id=payload.sync_member_department_id,
        is_active=payload.is_active,
    )
    await _feishu_config_repo.save(db, config)
    return _feishu_config_to_response(config)


async def _effective_feishu_credentials(
    db: AsyncSession,
    payload: FeishuConfigUpsert | None = None,
) -> tuple[str, str, str, str]:
    settings = get_settings()
    stored = await _feishu_config_repo.get_active(db)

    app_id = (
        (payload.app_id if payload else None) or (stored.app_id if stored else None) or settings.feishu.platform.app_id
    )
    encrypted_secret = stored.encrypted_app_secret if stored else ""
    try:
        app_secret = (
            payload.app_secret
            if payload and payload.app_secret
            else decrypt_secret(encrypted_secret)
            if encrypted_secret
            else settings.feishu.platform.app_secret
        )
    except RuntimeError as exc:
        raise _secret_runtime_error(exc) from exc
    root_id = (
        (payload.sync_root_department_id if payload else None)
        or (stored.sync_root_department_id if stored else None)
        or settings.feishu.platform.sync_root_dept_id
        or "0"
    )
    member_id = (
        (payload.sync_member_department_id if payload else None)
        or (stored.sync_member_department_id if stored else None)
        or settings.feishu.platform.sync_member_dept_id
        or root_id
    )
    if not app_id or not app_secret:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Livzon 助手飞书 App ID 或 App Secret 未配置",
        )
    return app_id, app_secret, root_id, member_id


def _diagnostic_status(steps: list[FeishuDiagnosticStep]) -> str:
    if any(step.status == "error" for step in steps):
        return "error"
    if any(step.status == "warning" for step in steps):
        return "warning"
    return "ok"


async def diagnose_livzon_feishu_config(
    db: AsyncSession,
    payload: FeishuConfigUpsert | None = None,
) -> FeishuDiagnosticResult:
    from app.platform.integrations.feishu.contact import (
        find_users_by_department,
        get_all_departments,
        get_contact_scope,
    )
    from app.platform.integrations.feishu.utils import get_tenant_access_token

    steps: list[FeishuDiagnosticStep] = []
    departments: list[dict[str, Any]] = []
    users: list[dict[str, Any]] = []
    scope: dict[str, Any] = {}
    stored = await _feishu_config_repo.get_active(db)

    try:
        app_id, app_secret, root_id, member_id = await _effective_feishu_credentials(db, payload)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_400_BAD_REQUEST:
            raise
        steps.append(
            FeishuDiagnosticStep(
                name="应用凭证",
                status="error",
                message="Livzon 助手飞书 App ID 或 App Secret 未配置",
                suggestion="请在系统设置的 Livzon 助手飞书设置中填写自建应用凭证。",
            )
        )
        return FeishuDiagnosticResult(
            status="error",
            message="Livzon 助手飞书配置不完整",
            steps=steps,
        )

    try:
        token = await get_tenant_access_token(
            app_id,
            app_secret,
            cache_key=f"livzon-assistant:{app_id}",
        )
        steps.append(
            FeishuDiagnosticStep(
                name="tenant_access_token",
                status="ok",
                message="已成功获取 tenant_access_token。",
            )
        )
    except Exception as exc:
        steps.append(
            FeishuDiagnosticStep(
                name="tenant_access_token",
                status="error",
                message=f"获取 tenant_access_token 失败：{exc}",
                suggestion=("请确认 App ID / App Secret 正确，且应用已发布或处于可调用状态。"),
            )
        )
        result = FeishuDiagnosticResult(
            status="error",
            message="Livzon 助手飞书认证失败",
            steps=steps,
        )
        await _save_diagnostic_result(db, stored, result)
        return result

    try:
        scope = await get_contact_scope(
            app_id=app_id,
            app_secret=app_secret,
            tenant_access_token=token,
        )
        scope_department_count = len(scope.get("department_ids") or [])
        scope_user_count = len(scope.get("user_ids") or [])
        scope_group_count = len(scope.get("group_ids") or [])
        steps.append(
            FeishuDiagnosticStep(
                name="通讯录授权范围",
                status="ok" if scope_department_count or scope_user_count or scope_group_count else "warning",
                message=(
                    "当前应用通讯录授权范围："
                    f"部门 {scope_department_count} 个，"
                    f"用户 {scope_user_count} 名，"
                    f"用户组 {scope_group_count} 个。"
                ),
                suggestion=None
                if scope_department_count or scope_user_count or scope_group_count
                else ("飞书开放平台的权限开通后，还需要在“通讯录权限范围”中授权可访问的部门或成员。"),
            )
        )
    except Exception as exc:
        steps.append(
            FeishuDiagnosticStep(
                name="通讯录授权范围",
                status="warning",
                message=f"读取通讯录授权范围失败：{exc}",
                suggestion=("请确认已开通 contact:scope:readonly，或在飞书开放平台检查通讯录权限范围是否已发布生效。"),
            )
        )

    try:
        # get_all_departments 内部自建客户端与 token（用平台应用凭证），不接受外部凭证参数；
        # 被检查的 Livzon 应用凭证已在上面「tenant_access_token」「通讯录授权范围」两步验证过。
        departments = await get_all_departments(root_department_id=root_id)
        steps.append(
            FeishuDiagnosticStep(
                name="部门列表",
                status="ok" if departments else "warning",
                message=(
                    f"读取到 {len(departments)} 个部门。" if departments else "部门 API 调用成功，但未读取到部门数据。"
                ),
                suggestion=None
                if departments
                else (
                    "请检查通讯录权限范围是否包含同步根部门；飞书要求使用 "
                    "fetch_child=true 获取子部门，并开通 "
                    "contact:department.base:readonly / "
                    "contact:department.organize:readonly。"
                ),
            )
        )
    except Exception as exc:
        steps.append(
            FeishuDiagnosticStep(
                name="部门列表",
                status="error",
                message=f"读取部门列表失败：{exc}",
                suggestion=(
                    "请开通 contact:department.base:readonly、"
                    "contact:department.organize:readonly，并确认通讯录权限范围。"
                ),
            )
        )

    sample_department_ids = []
    departments_with_members = (dept.get("department_id", "") for dept in departments if dept.get("member_count"))
    for dept_id in [
        member_id,
        *departments_with_members,
        *(dept.get("department_id", "") for dept in departments),
        *((scope.get("department_ids") or [])[:3]),
        root_id,
    ]:
        if dept_id and dept_id not in sample_department_ids:
            sample_department_ids.append(dept_id)

    sampled_department_id = ""
    if sample_department_ids:
        last_error: Exception | None = None
        tried_ids: list[str] = []
        try:
            for sample_department_id in sample_department_ids:
                tried_ids.append(sample_department_id)
                users = await find_users_by_department(sample_department_id)
                if users:
                    sampled_department_id = sample_department_id
                    break
            if not sampled_department_id and tried_ids:
                sampled_department_id = tried_ids[0]
            steps.append(
                FeishuDiagnosticStep(
                    name="部门用户",
                    status="ok" if users else "warning",
                    message=(
                        f"部门 {sampled_department_id} 读取到 {len(users)} 名用户。"
                        if users
                        else (f"已尝试部门 {', '.join(tried_ids[:5])}，API 调用成功，但未读取到用户。")
                    ),
                    suggestion=None
                    if users
                    else (
                        "请确认这些部门下存在直属成员；若成员在子部门，请配置成员同步部门"
                        "为有人的部门，或检查通讯录权限范围是否包含该部门成员，并开通 "
                        "contact:user.base:readonly。"
                    ),
                )
            )
        except Exception as exc:
            last_error = exc
            steps.append(
                FeishuDiagnosticStep(
                    name="部门用户",
                    status="error" if last_error else "warning",
                    message=f"读取部门用户失败：{last_error or exc}",
                    suggestion=("请开通 contact:user.base:readonly，并确认应用通讯录权限范围包含目标部门。"),
                )
            )
    else:
        steps.append(
            FeishuDiagnosticStep(
                name="部门用户",
                status="warning",
                message="没有可用于抽样的部门 ID。",
                suggestion="请配置成员同步部门 ID，或扩大通讯录权限范围后重试。",
            )
        )

    if users:
        has_department_ids = any(user.get("department_ids") for user in users)
        has_mobile = any(user.get("mobile") for user in users)
        has_email = any(user.get("email") for user in users)
        steps.extend(
            [
                FeishuDiagnosticStep(
                    name="用户部门关系",
                    status="ok" if has_department_ids else "warning",
                    message="已返回用户 department_ids 字段。"
                    if has_department_ids
                    else "用户可读取，但未返回 department_ids。",
                    suggestion=None if has_department_ids else "请开通 contact:user.department:readonly。",
                ),
                FeishuDiagnosticStep(
                    name="用户手机号",
                    status="ok" if has_mobile else "warning",
                    message="已返回至少一名用户手机号。" if has_mobile else "用户可读取，但未返回手机号。",
                    suggestion=None
                    if has_mobile
                    else ("请开通 contact:user.phone:readonly，并确认通讯录权限范围包含手机号字段。"),
                ),
                FeishuDiagnosticStep(
                    name="用户邮箱",
                    status="ok" if has_email else "warning",
                    message="已返回至少一名用户邮箱。" if has_email else "用户可读取，但未返回邮箱。",
                    suggestion=None
                    if has_email
                    else ("请开通 contact:user.email:readonly，并确认通讯录权限范围包含邮箱字段。"),
                ),
            ]
        )

    status_value = _diagnostic_status(steps)
    result = FeishuDiagnosticResult(
        status=status_value,
        message={
            "ok": "Livzon 助手飞书配置可用。",
            "warning": "Livzon 助手飞书配置可连接，但部分通讯录数据不可见。",
            "error": "Livzon 助手飞书配置存在错误。",
        }[status_value],
        steps=steps,
        department_count=len(departments),
        sample_user_count=len(users),
    )
    await _save_diagnostic_result(db, stored, result)
    return result


async def _save_diagnostic_result(
    db: AsyncSession,
    config: FeishuConfig | None,
    result: FeishuDiagnosticResult,
) -> None:
    if config is None:
        return
    config.last_diagnostic_status = result.status
    config.last_diagnostic_message = result.message
    config.last_diagnostic_result = json.dumps(result.model_dump(), ensure_ascii=False)
    config.last_diagnosed_at = datetime.now(UTC)
    await db.flush()


async def run_livzon_feishu_sync_all(db: AsyncSession) -> dict[str, Any]:
    from app.platform.integrations.feishu.contact import get_contact_scope
    from app.platform.integrations.feishu.sync import (
        sync_departments,
        sync_members,
        sync_users_by_ids,
    )

    config = await _feishu_config_repo.get_active(db)
    app_id, app_secret, root_id, member_id = await _effective_feishu_credentials(db)

    scope: dict[str, Any] = {}
    scope_department_ids: list[str] = []
    scope_user_ids: list[str] = []
    try:
        scope = await get_contact_scope(app_id=app_id, app_secret=app_secret)
        scope_department_ids = scope.get("department_ids") or []
        scope_user_ids = scope.get("user_ids") or []
    except Exception:
        logger.exception("Failed to read Livzon Feishu contact scope before sync")

    department_targets = [root_id]
    member_targets = [member_id]
    if root_id == "0" and scope_department_ids:
        department_targets = scope_department_ids
    if member_id == "0" and scope_department_ids:
        member_targets = scope_department_ids

    dept_results: list[dict[str, Any]] = []
    dept_errors: list[str] = []
    for department_id in dict.fromkeys(department_targets):
        try:
            dept_results.append(
                await sync_departments(
                    department_id,
                    app_id=app_id,
                    app_secret=app_secret,
                )
            )
        except Exception as exc:
            logger.exception("Livzon Feishu department sync failed: %s", department_id)
            dept_errors.append(f"{department_id}: {exc}")

    member_results: list[dict[str, Any]] = []
    member_errors: list[str] = []
    for department_id in dict.fromkeys(member_targets):
        try:
            member_results.append(
                await sync_members(
                    department_id,
                    app_id=app_id,
                    app_secret=app_secret,
                )
            )
        except Exception as exc:
            logger.exception("Livzon Feishu member sync failed: %s", department_id)
            member_errors.append(f"{department_id}: {exc}")

    direct_user_result = {"user_count": 0, "elapsed": 0}
    if scope_user_ids:
        direct_user_result = await sync_users_by_ids(
            scope_user_ids,
            user_id_type="user_id",
            app_id=app_id,
            app_secret=app_secret,
        )

    dept_count = sum(item.get("dept_count", 0) for item in dept_results)
    member_count = sum(item.get("user_count", 0) for item in member_results)
    direct_user_count = direct_user_result.get("user_count", 0)
    total_user_count = member_count + direct_user_count
    nested_member_errors = [str(error) for result in member_results for error in result.get("errors", [])]
    all_errors = dept_errors + member_errors + nested_member_errors

    if not dept_results and not member_results and not direct_user_count:
        message = (
            "同步失败：当前 Livzon 助手飞书应用没有可同步的通讯录数据。请检查通讯录权限范围是否包含目标部门或用户。"
        )
        if all_errors:
            message = f"{message} 错误：{'; '.join(all_errors)}"
        if config is not None:
            config.last_sync_status = "error"
            config.last_sync_message = message
            config.last_synced_at = datetime.now(UTC)
            await db.flush()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, message)

    sync_status = "warning" if all_errors else "ok"
    sync_message = f"同步完成：部门 {dept_count} 个，部门用户 {member_count} 名，直接授权用户 {direct_user_count} 名。"
    if sync_status == "warning":
        sync_message = f"{sync_message} 部分部门同步失败：{'; '.join(all_errors)}"
    if config is not None:
        config.last_sync_status = sync_status
        config.last_sync_message = sync_message
        config.last_synced_at = datetime.now(UTC)
        await db.flush()
    return {
        "scope": {
            "department_count": len(scope_department_ids),
            "user_count": len(scope_user_ids),
            "group_count": len(scope.get("group_ids") or []),
        },
        "department_targets": department_targets,
        "member_targets": member_targets,
        "departments": {
            "dept_count": dept_count,
            "results": dept_results,
            "errors": dept_errors,
        },
        "members": {
            "user_count": total_user_count,
            "department_user_count": member_count,
            "direct_user_count": direct_user_count,
            "results": member_results,
            "direct_user_result": direct_user_result,
            "errors": member_errors + nested_member_errors,
        },
        "status": sync_status,
        "message": sync_message,
    }


async def sync_livzon_feishu_contacts_all() -> None:
    """后台任务入口：自建会话跑一次「部门 + 成员」全量同步。

    全量同步耗时可达数十秒，不适合放在 HTTP 请求里（项目规范要求超过 5 秒的操作走后台任务），
    因此由 `spawn_task` 触发；结果（last_sync_status / last_sync_message / last_synced_at）
    由 run_livzon_feishu_sync_all 写入飞书配置。后台任务抛异常没人接，故这里兜底后只记日志。
    """
    try:
        async with async_session_factory() as db:
            await run_livzon_feishu_sync_all(db)
            await db.commit()
    except Exception:
        logger.exception("Livzon Feishu contacts sync (all) failed")


async def record_member_sync_result(result: dict[str, Any]) -> None:
    """把「每日自动成员同步」的结果写入飞书配置的 last_sync_* 字段。

    手动触发的全量同步（run_livzon_feishu_sync_all）已自行写状态；每日 00:00 的
    自动同步直接调 sync_members，此前不写状态，导致「系统设置 → 飞书设置」里看不到
    自动同步的结果。此函数补齐这条链路；失败只记日志，不影响同步本身。
    """
    try:
        async with async_session_factory() as db:
            config = await _feishu_config_repo.get_active(db)
            if config is None:
                return
            errors = result.get("errors") or []
            user_count = result.get("user_count", 0)
            config.last_synced_at = datetime.now(UTC)
            if errors:
                config.last_sync_status = "warning"
                preview = "; ".join(str(e) for e in errors[:5])
                config.last_sync_message = f"自动同步完成：成员 {user_count} 名，部分失败：{preview}"
            else:
                config.last_sync_status = "ok"
                config.last_sync_message = f"自动同步完成：成员 {user_count} 名"
            await db.commit()
    except Exception:
        logger.exception("记录成员自动同步结果失败")


async def _active_livzon_feishu_credentials(db: AsyncSession) -> tuple[str, str]:
    config = await _feishu_config_repo.get_active(db)
    if config is None or not config.app_id or not config.encrypted_app_secret:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Livzon 助手飞书 App ID 或 App Secret 未配置",
        )
    try:
        app_secret = decrypt_secret(config.encrypted_app_secret)
    except RuntimeError as exc:
        raise _secret_runtime_error(exc) from exc
    if not app_secret:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Livzon 助手飞书 App Secret 未配置",
        )
    return config.app_id, app_secret


def _dedupe_user_ids(user_ids: list[UUID]) -> list[UUID]:
    return list(dict.fromkeys(user_ids))


def _empty_message_result(user_id: UUID, message: str) -> dict[str, Any]:
    return {
        "user_id": str(user_id),
        "name": None,
        "feishu_open_id": None,
        "status": "failed",
        "message_id": None,
        "error_code": None,
        "error_message": message,
    }


def _message_shape(
    *,
    value_level: str,
    structured: bool,
    requires_business_action: bool,
    message_form: str = "auto",
) -> str:
    if requires_business_action:
        expected = "interactive_card"
    elif value_level == "low" and not structured:
        expected = "text"
    else:
        expected = "card"
    if message_form != "auto" and message_form != expected:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"消息形态不符合 Livzon 助手规则：当前应使用 {expected}",
        )
    return expected


def _normalize_card_actions(actions: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    raw_actions = actions or [
        {"action_key": "start_processing", "label": "开始处理"},
        {"action_key": "mark_done", "label": "标记完成"},
    ]
    normalized: list[dict[str, str]] = []
    for item in raw_actions:
        action_key = str(item.get("action_key") or "").strip()
        if action_key not in ALLOWED_CARD_ACTIONS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"不支持的交互卡片动作：{action_key}",
            )
        label = str(item.get("label") or ALLOWED_CARD_ACTIONS[action_key]).strip()
        normalized.append(
            {
                "action_key": action_key,
                "label": label[:100],
                "button_type": str(item.get("button_type") or "primary"),
            }
        )
    return normalized


def _callback_action_status(action_key: str) -> str:
    if action_key == "reject":
        return "rejected"
    return "processed"


def _write_card_action_audit(
    db: AsyncSession,
    *,
    action: FeishuCardAction,
) -> None:
    if not hasattr(db, "add"):
        return
    db.add(
        AuditLog(
            request_id=str(action.card_id) if action.card_id else None,
            user_id=action.local_user_id,
            method="FEISHU",
            path="/api/v1/identity/feishu/card-callback",
            status_code=200,
            resource_type="feishu_card_action",
            resource_id=action.id,
            action="feishu_card_action_callback",
            new_value={
                "action_key": action.action_key,
                "status": action.status,
                "clicked_open_id": action.clicked_open_id,
            },
            extra={
                "message_id": action.message_id,
                "card_id": action.card_id,
                "recipient_open_id": action.recipient_open_id,
            },
        )
    )


async def _send_livzon_feishu_message(
    db: AsyncSession,
    *,
    user_ids: list[UUID],
    msg_type: str,
    content: str,
) -> dict[str, Any]:
    from app.platform.integrations.feishu.im import send_feishu_message
    from app.platform.integrations.feishu.utils import get_tenant_access_token

    app_id, app_secret = await _active_livzon_feishu_credentials(db)
    token = await get_tenant_access_token(
        app_id,
        app_secret,
        cache_key=f"livzon-assistant:{app_id}",
    )

    results: list[dict[str, Any]] = []
    for user_id in _dedupe_user_ids(user_ids):
        user = await _repo.get_by_id(db, user_id)
        if user is None:
            results.append(_empty_message_result(user_id, "本地用户不存在"))
            continue
        if not user.feishu_open_id:
            results.append(
                {
                    "user_id": str(user.id),
                    "name": user.name,
                    "feishu_open_id": None,
                    "status": "failed",
                    "message_id": None,
                    "error_code": None,
                    "error_message": "用户缺少 feishu_open_id，请先同步通讯录",
                }
            )
            continue

        try:
            sent = await send_feishu_message(
                tenant_access_token=token,
                receive_id=user.feishu_open_id,
                receive_id_type="open_id",
                msg_type=msg_type,
                content=content,
            )
        except Exception as exc:
            logger.exception(
                "Livzon Feishu message send failed: user_id=%s",
                user.id,
            )
            results.append(
                {
                    "user_id": str(user.id),
                    "name": user.name,
                    "feishu_open_id": user.feishu_open_id,
                    "status": "failed",
                    "message_id": None,
                    "error_code": None,
                    "error_message": str(exc),
                }
            )
            continue

        results.append(
            {
                "user_id": str(user.id),
                "name": user.name,
                "feishu_open_id": user.feishu_open_id,
                "status": "sent" if sent.ok else "failed",
                "message_id": sent.message_id,
                "error_code": sent.code if not sent.ok else None,
                "error_message": sent.error_message if not sent.ok else None,
            }
        )

    success_count = sum(1 for item in results if item["status"] == "sent")
    failed_count = len(results) - success_count
    return {
        "total": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results,
    }


async def _send_livzon_feishu_callback_card(
    db: AsyncSession,
    *,
    user_ids: list[UUID],
    title: str,
    markdown: str,
    header_template: str,
    actions: list[dict[str, Any]] | None,
    business_ref: dict[str, Any] | None,
) -> dict[str, Any]:
    from app.platform.integrations.feishu.im import (
        build_callback_card_content,
        send_feishu_message,
    )
    from app.platform.integrations.feishu.utils import get_tenant_access_token

    settings = get_settings()
    config = await _feishu_config_repo.get_active(db)
    if config is None or (
        not config.card_callback_verification_token and not settings.LIVZON_FEISHU_CARD_CALLBACK_WS_ENABLED
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            (
                "Livzon 助手飞书交互卡片回调未配置。HTTP 回调需要 "
                "Verification Token；开发环境可开启长连接 "
                "LIVZON_FEISHU_CARD_CALLBACK_WS_ENABLED=true。"
            ),
        )
    app_id, app_secret = await _active_livzon_feishu_credentials(db)
    token = await get_tenant_access_token(
        app_id,
        app_secret,
        cache_key=f"livzon-assistant:{app_id}",
    )
    normalized_actions = _normalize_card_actions(actions)
    results: list[dict[str, Any]] = []
    expires_at = datetime.now(UTC) + timedelta(days=14)

    for user_id in _dedupe_user_ids(user_ids):
        user = await _repo.get_by_id(db, user_id)
        if user is None:
            results.append(_empty_message_result(user_id, "本地用户不存在"))
            continue
        if not user.feishu_open_id:
            results.append(
                {
                    "user_id": str(user.id),
                    "name": user.name,
                    "feishu_open_id": None,
                    "status": "failed",
                    "message_id": None,
                    "error_code": None,
                    "error_message": "用户缺少 feishu_open_id，请先同步通讯录",
                }
            )
            continue

        card_id = f"livzon-{secrets.token_hex(12)}"
        card_actions: list[dict[str, str]] = []
        for item in normalized_actions:
            action = await _feishu_card_action_repo.create(
                db,
                message_id=None,
                card_id=card_id,
                local_user_id=user.id,
                recipient_open_id=user.feishu_open_id,
                business_ref=business_ref,
                action_key=item["action_key"],
                action_label=item["label"],
                expires_at=expires_at,
            )
            card_actions.append(
                {
                    "action_id": str(action.id),
                    "action_key": item["action_key"],
                    "label": item["label"],
                    "button_type": item["button_type"],
                }
            )
        content = build_callback_card_content(
            title=title,
            markdown=markdown,
            actions=card_actions,
            header_template=header_template,
        )
        try:
            sent = await send_feishu_message(
                tenant_access_token=token,
                receive_id=user.feishu_open_id,
                receive_id_type="open_id",
                msg_type="interactive",
                content=content,
            )
        except Exception as exc:
            logger.exception(
                "Livzon Feishu callback card send failed: user_id=%s",
                user.id,
            )
            results.append(
                {
                    "user_id": str(user.id),
                    "name": user.name,
                    "feishu_open_id": user.feishu_open_id,
                    "status": "failed",
                    "message_id": None,
                    "error_code": None,
                    "error_message": str(exc),
                    "message_form": "interactive_card",
                }
            )
            continue
        await _feishu_card_action_repo.set_message_id_for_card(
            db,
            card_id=card_id,
            message_id=sent.message_id,
        )
        results.append(
            {
                "user_id": str(user.id),
                "name": user.name,
                "feishu_open_id": user.feishu_open_id,
                "status": "sent" if sent.ok else "failed",
                "message_id": sent.message_id,
                "error_code": sent.code if not sent.ok else None,
                "error_message": sent.error_message if not sent.ok else None,
                "message_form": "interactive_card",
                "callback_action_count": len(card_actions),
            }
        )

    success_count = sum(1 for item in results if item["status"] == "sent")
    failed_count = len(results) - success_count
    return {
        "message_form": "interactive_card",
        "total": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results,
    }


async def send_livzon_feishu_text_message(
    db: AsyncSession,
    *,
    user_ids: list[UUID],
    text: str,
) -> dict[str, Any]:
    from app.platform.integrations.feishu.im import build_text_message_content

    return await _send_livzon_feishu_message(
        db,
        user_ids=user_ids,
        msg_type="text",
        content=build_text_message_content(text),
    )


async def send_livzon_feishu_card_message(
    db: AsyncSession,
    *,
    user_ids: list[UUID],
    title: str,
    markdown: str,
    header_template: str = "blue",
    button_text: str | None = None,
    button_url: str | None = None,
) -> dict[str, Any]:
    from app.platform.integrations.feishu.im import build_simple_card_content

    return await _send_livzon_feishu_message(
        db,
        user_ids=user_ids,
        msg_type="interactive",
        content=build_simple_card_content(
            title=title,
            markdown=markdown,
            header_template=header_template,
            button_text=button_text,
            button_url=button_url,
        ),
    )


async def send_livzon_feishu_message(
    db: AsyncSession,
    *,
    user_ids: list[UUID],
    text: str,
    title: str | None = None,
    markdown: str | None = None,
    value_level: str = "low",
    structured: bool = False,
    requires_business_action: bool = False,
    actions: list[dict[str, Any]] | None = None,
    business_ref: dict[str, Any] | None = None,
    header_template: str = "blue",
    message_form: str = "auto",
) -> dict[str, Any]:
    shape = _message_shape(
        value_level=value_level,
        structured=structured,
        requires_business_action=requires_business_action,
        message_form=message_form,
    )
    if shape == "text":
        result = await send_livzon_feishu_text_message(
            db,
            user_ids=user_ids,
            text=text,
        )
        result["message_form"] = "text"
        return result
    card_title = title or "Livzon 助手通知"
    card_markdown = markdown or text
    if shape == "card":
        result = await send_livzon_feishu_card_message(
            db,
            user_ids=user_ids,
            title=card_title,
            markdown=card_markdown,
            header_template=header_template,
        )
        result["message_form"] = "card"
        return result
    return await _send_livzon_feishu_callback_card(
        db,
        user_ids=user_ids,
        title=card_title,
        markdown=card_markdown,
        header_template=header_template,
        actions=actions,
        business_ref=business_ref,
    )


def _verify_feishu_callback_signature(
    *,
    encrypt_key: str | None,
    raw_body: bytes,
    timestamp: str | None,
    nonce: str | None,
    signature: str | None,
) -> bool:
    # 未配置 Encrypt Key 时无法做签名校验，此时由调用方的 verification token 校验兜底。
    if not encrypt_key:
        return True
    # 配置了 Encrypt Key 就必须提供完整签名材料，缺任何一项都判失败（fail-closed），
    # 否则「删掉签名头」即可绕过校验。
    if not timestamp or not nonce or not signature:
        return False
    raw = f"{timestamp}{nonce}{encrypt_key}".encode() + raw_body
    expected = hashlib.sha256(raw).hexdigest()
    return hmac.compare_digest(expected, signature)


def _callback_payload_token(payload: dict[str, Any]) -> str | None:
    token = payload.get("token")
    if isinstance(token, str):
        return token
    header = payload.get("header")
    if isinstance(header, dict) and isinstance(header.get("token"), str):
        return header["token"]  # type: ignore[no-any-return]
    return None


def _extract_callback_action(
    payload: dict[str, Any],
) -> tuple[str | None, str | None, str | None]:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
    action = event.get("action") if isinstance(event, dict) else None
    value = action.get("value") if isinstance(action, dict) else None
    action_id = value.get("action_id") if isinstance(value, dict) else None
    action_key = value.get("action_key") if isinstance(value, dict) else None
    operator = event.get("operator") if isinstance(event, dict) else None
    open_id = None
    if isinstance(operator, dict):
        open_id = operator.get("open_id") or operator.get("user_id")
    user = event.get("user") if isinstance(event, dict) else None
    if not open_id and isinstance(user, dict):
        open_id = user.get("open_id") or user.get("user_id")
    return (
        action_id if isinstance(action_id, str) else None,
        action_key if isinstance(action_key, str) else None,
        open_id if isinstance(open_id, str) else None,
    )


async def handle_livzon_feishu_card_callback(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
    raw_body: bytes,
    timestamp: str | None = None,
    nonce: str | None = None,
    signature: str | None = None,
) -> dict[str, Any]:
    config = await _feishu_config_repo.get_active(db)
    if config is None or not config.card_callback_verification_token:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Livzon 助手飞书卡片回调未配置",
        )
    encrypt_key = None
    if config.encrypted_card_callback_encrypt_key:
        try:
            encrypt_key = decrypt_secret(config.encrypted_card_callback_encrypt_key)
        except RuntimeError as exc:
            raise _secret_runtime_error(exc) from exc
    if not _verify_feishu_callback_signature(
        encrypt_key=encrypt_key,
        raw_body=raw_body,
        timestamp=timestamp,
        nonce=nonce,
        signature=signature,
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "飞书回调签名校验失败")
    if "encrypt" in payload:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "暂不支持加密后的飞书卡片回调 payload，请关闭加密或使用签名校验",
        )
    token = _callback_payload_token(payload)
    if not token or not hmac.compare_digest(
        token,
        config.card_callback_verification_token,
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "飞书回调 token 校验失败")
    challenge = payload.get("challenge")
    if isinstance(challenge, str):
        return {"challenge": challenge}

    return await handle_livzon_feishu_card_action_event(db, payload=payload)


async def handle_livzon_feishu_card_action_event(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Handle authenticated Livzon Feishu card action payloads.

    HTTP callbacks validate verification token/signature before calling this.
    WebSocket callbacks are authenticated by the Feishu long-connection channel.
    """
    action_id, action_key, clicked_open_id = _extract_callback_action(payload)
    if not action_id or not action_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "飞书回调缺少 action_id")
    action = await _feishu_card_action_repo.get_pending_by_id(db, action_id)
    if action is None:
        return {"toast": {"type": "warning", "content": "操作不存在或已删除"}}
    if action.action_key != action_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "飞书回调动作不匹配")
    now = datetime.now(UTC)
    if action.expires_at and action.expires_at < now:
        action.status = "expired"
        action.clicked_open_id = clicked_open_id
        action.executed_at = now
        action.callback_summary = {
            "action_id": action_id,
            "action_key": action_key,
            "clicked_open_id": clicked_open_id,
            "result": "expired",
        }
        _write_card_action_audit(db, action=action)
        await db.flush()
        return {"toast": {"type": "warning", "content": "该操作已过期"}}
    if action.status != "pending":
        return {"toast": {"type": "info", "content": "该操作已处理"}}

    action.status = _callback_action_status(action_key)
    action.clicked_open_id = clicked_open_id
    action.executed_at = now
    action.callback_summary = {
        "action_id": action_id,
        "action_key": action_key,
        "clicked_open_id": clicked_open_id,
        "status": action.status,
    }
    _write_card_action_audit(db, action=action)
    await db.flush()
    return {
        "toast": {
            "type": "success",
            "content": f"已记录：{action.action_label}",
        }
    }


def _apply_contact_profile(user: User, detail: dict[str, Any]) -> None:
    """把通讯录详情里的 部门 / 职务 / 工号 / 企业邮箱 写入用户记录（只补齐非空值）。"""
    employee_no = (detail.get("employee_no") or "").strip()
    if employee_no:
        user.employee_no = employee_no

    job_title = (detail.get("job_title") or "").strip()
    if job_title:
        user.position = job_title

    # 部门名取部门路径的最后一级（最具体的部门）
    department_path = detail.get("department_path") or []
    department_name = ""
    if department_path:
        department_name = (department_path[-1].get("department_name") or "").strip()
    if department_name:
        user.department = department_name

    department_ids = detail.get("department_ids") or []
    if department_ids:
        user.feishu_department_ids = json.dumps(list(department_ids), ensure_ascii=False)

    enterprise_email = (detail.get("enterprise_email") or "").strip()
    if enterprise_email:
        user.enterprise_email = enterprise_email

    # 头像三档（通讯录返回的是直链 URL）
    for field in ("avatar_url", "avatar_thumb", "avatar_middle", "avatar_big"):
        value = (detail.get(field) or "").strip()
        if value:
            setattr(user, field, value)

    # 飞书侧已冻结（离职/停用）→ 单向禁用平台账号。
    # 注意只做单向：飞书恢复正常时不自动启用，避免覆盖管理员在平台上的手工禁用。
    if detail.get("is_frozen"):
        user.status = "disabled"


async def enrich_user_from_feishu_contact(
    user: User,
    *,
    open_id: str | None,
    feishu_user_id: str | None,
) -> None:
    """登录后尽力补齐通讯录字段（部门 / 职务 / 工号 / 企业邮箱）。

    背景：登录用的 `authen/v1/user_info` 不返回部门、职务、工号，
    必须另外调通讯录接口 `contact/v3/users/{id}`。
    通讯录接口需要额外权限，未开通或查不到时**只记日志、不影响登录**——
    宁可只有登录信息，也不能让用户登不进来。
    """
    identifier = (open_id or "").strip() or (feishu_user_id or "").strip()
    if not identifier:
        return
    id_type = "open_id" if (open_id or "").strip() else "user_id"
    try:
        from app.platform.integrations.feishu.contact import get_user_detail

        detail = await get_user_detail(identifier, user_id_type=id_type)
        if not detail:
            logger.warning(
                "飞书通讯录详情为空，跳过资料补齐（检查应用是否已开通通讯录权限）: %s=%s",
                id_type,
                identifier,
            )
            return
        _apply_contact_profile(user, detail)
        logger.info(
            "已补齐飞书通讯录资料: open_id=%s 部门=%s 职务=%s 工号=%s",
            open_id,
            user.department,
            user.position,
            user.employee_no,
        )
    except Exception:  # noqa: BLE001 - 资料补齐失败绝不能影响登录主流程
        logger.warning("补齐飞书通讯录资料失败（不影响登录）: %s", identifier, exc_info=True)


async def handle_oauth_callback(
    db: AsyncSession,
    code: str,
) -> tuple[User, str]:
    """Complete the OAuth flow: exchange code → get user info → upsert → JWT.

    Returns (user, jwt_token).
    """
    oauth = FeishuOAuthClient.from_settings()

    # 1. Exchange authorization code for tokens (v2 endpoint)
    token_data = await oauth.exchange_code(code)
    user_access_token = token_data["access_token"]

    # 2. Fetch user profile from Feishu (v1 user_info endpoint)
    #    Response fields: name, en_name, avatar_url, avatar_thumb,
    #    avatar_middle, avatar_big, open_id, union_id, email,
    #    enterprise_email, user_id, mobile, tenant_key
    info = await oauth.get_user_info(user_access_token)

    open_id = info.get("open_id", "")
    user_id = info.get("user_id") or None  # Convert empty to None
    union_id = info.get("union_id") or None  # Convert empty to None
    name = info.get("name", "")
    en_name = info.get("en_name")
    # 头像：新版接口返回 avatar 对象（avatar_72/240/640），旧版是 avatar_* 平铺字段，两种都兼容
    avatar_obj = info.get("avatar") or {}
    avatar_url = (
        info.get("avatar_url")
        or info.get("avatar_middle")
        or avatar_obj.get("avatar_640")
        or avatar_obj.get("avatar_240")
    )
    avatar_thumb = info.get("avatar_thumb") or avatar_obj.get("avatar_72")
    avatar_middle = info.get("avatar_middle") or avatar_obj.get("avatar_240")
    avatar_big = info.get("avatar_big") or avatar_obj.get("avatar_640")
    email = info.get("email") or info.get("enterprise_email")
    enterprise_email = info.get("enterprise_email")
    mobile = info.get("mobile")
    tenant_key = info.get("tenant_key")

    if not open_id:
        raise ValueError("Feishu user info missing open_id")

    # 3. Upsert user in local DB
    user = await _repo.get_by_feishu_open_id(db, open_id)
    if user is None:
        # Also try matching by feishu_user_id in case user was synced earlier
        user = await _repo.get_by_feishu_user_id(db, user_id) if user_id else None

    if user is None:
        user = await _repo.create(
            db,
            name=name,
            username=await allocate_default_username(db),
            feishu_user_id=user_id,
            feishu_open_id=open_id,
            feishu_union_id=union_id,
            en_name=en_name,
            email=email,
            enterprise_email=enterprise_email,
            mobile=mobile,
            avatar_url=avatar_url,
            avatar_thumb=avatar_thumb,
            avatar_middle=avatar_middle,
            avatar_big=avatar_big,
            tenant_key=tenant_key,
            status="active",
            auth_source="feishu",
        )
        logger.info("Created new user: %s (open_id=%s)", name, open_id)
    else:
        # Update profile info on each login
        user.name = name or user.name
        user.feishu_user_id = user_id or user.feishu_user_id
        user.feishu_union_id = union_id or user.feishu_union_id
        user.en_name = en_name or user.en_name
        user.email = email or user.email
        user.enterprise_email = enterprise_email or user.enterprise_email
        user.mobile = mobile or user.mobile
        user.avatar_url = avatar_url or user.avatar_url
        user.avatar_thumb = avatar_thumb or user.avatar_thumb
        user.avatar_middle = avatar_middle or user.avatar_middle
        user.avatar_big = avatar_big or user.avatar_big
        user.tenant_key = tenant_key or user.tenant_key
        user.auth_source = user.auth_source or "feishu"
        if _matches_admin_whitelist(user, get_settings().SSO_ADMIN_IDENTIFIERS):
            pass  # role column removed
        logger.info("Updated user: %s (open_id=%s)", user.name, open_id)

    # 3.05 补齐本地用户名（同步进来/历史建号只有飞书字段的账号在这里补）
    await ensure_default_username(db, user)

    # 3.1 登录时补齐通讯录资料（部门 / 职务 / 工号 / 企业邮箱 / 冻结状态）
    #     user_info 不返回这些字段，需另调 contact/v3/users；失败只记日志，不影响登录
    await enrich_user_from_feishu_contact(user, open_id=open_id, feishu_user_id=user_id)

    # 放在补齐之后判断：若本次发现飞书侧已冻结，当场就拒绝登录
    if user.status == "disabled":
        raise PermissionError("User account is disabled")

    user.last_login_at = datetime.now(UTC)
    await db.commit()

    # 4. Generate JWT
    token = generate_jwt(user)
    return user, token


def generate_jwt(user: User) -> str:
    """Generate a JWT token for the given user.

    含 `jti`（token 唯一 ID）：会话管理据此在 Redis 索引 / 吊销（踢下线）。
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "open_id": user.feishu_open_id,
        "name": user.name,
        "auth_source": user.auth_source,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=settings.JWT_EXPIRE_SECONDS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


async def get_or_create_e2e_user(db: AsyncSession) -> User:
    """Get or create the e2e test user. Only called in dev/test environments."""
    user = await _repo.get_by_feishu_open_id(db, "test-user-e2e")
    if user:
        user.status = "active"
        return user

    user = User(
        name="E2E Test User",
        username="e2e-test-user",
        feishu_open_id="test-user-e2e",
        feishu_user_id="test-user-e2e",
        status="active",
        auth_source="local",
        email="e2e-test@dazah.local",
    )
    db.add(user)
    await db.flush()
    return user


MAX_LOGIN_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60


async def authenticate_local_user(db: AsyncSession, *, username: str, password: str) -> tuple[User, str]:
    user = await _repo.get_by_login_identifier(db, username)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")

    now = datetime.now(UTC)
    if user.locked_until is not None and user.locked_until > now:
        raise HTTPException(status.HTTP_423_LOCKED, "登录失败次数过多，账号已临时锁定，请稍后再试")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_LOGIN_FAILURES:
            user.locked_until = now + timedelta(seconds=LOCKOUT_SECONDS)
            user.failed_login_attempts = 0
        await db.flush()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")

    if user.status == "disabled":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已禁用")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    await db.flush()
    return user, generate_jwt(user)


# 飞书身份字段（绑定/解绑时整体搬迁或清空）
FEISHU_IDENTITY_FIELDS: tuple[str, ...] = (
    "feishu_user_id",
    "feishu_open_id",
    "feishu_union_id",
    "avatar_url",
    "avatar_thumb",
    "avatar_middle",
    "avatar_big",
    "feishu_department_ids",
)


async def bind_feishu_user(
    db: AsyncSession,
    *,
    target: User,
    source: User,
    operator_id: UUID | None = None,
) -> dict[str, int]:
    """把一条飞书用户记录「合并」进目标账号（绑定飞书登录）。

    做四件事：
    1. 迁移角色授权（按 role_id + scope_type 去重：目标已有同款则软删源侧那条）；
    2. 搬迁飞书身份字段（源侧清空，避免 feishu_user_id 唯一索引冲突）；
    3. 补齐目标账号缺失的基础资料（邮箱 / 手机 / 工号 / 部门 / 岗位）；
    4. 软删源记录（其历史引用继续挂在原 id 上，不迁移）。

    目标账号保留自己的 username / password_hash / auth_source —— 本地账号合并后
    既能继续用账号密码登录，也能用飞书登录（登录回调按 feishu_open_id 命中它）。
    """
    from app.platform.permission.models import UserRoleGrant

    # 1. 迁移授权
    target_grants = (
        (
            await db.execute(
                select(UserRoleGrant).where(
                    UserRoleGrant.user_id == target.id,
                    UserRoleGrant.is_deleted == False,  # noqa: E712
                )
            )
        )
        .scalars()
        .all()
    )
    existing_keys = {(grant.role_id, grant.scope_type) for grant in target_grants}

    source_grants = (
        (
            await db.execute(
                select(UserRoleGrant).where(
                    UserRoleGrant.user_id == source.id,
                    UserRoleGrant.is_deleted == False,  # noqa: E712
                )
            )
        )
        .scalars()
        .all()
    )

    moved = 0
    deduplicated = 0
    for grant in source_grants:
        if (grant.role_id, grant.scope_type) in existing_keys:
            grant.is_deleted = True
            deduplicated += 1
        else:
            grant.user_id = target.id
            grant.version += 1
            moved += 1
        grant.updated_by = operator_id

    # 2. 身份字段搬迁
    for field in FEISHU_IDENTITY_FIELDS:
        value = getattr(source, field, None)
        setattr(source, field, None)
        if value and not getattr(target, field, None):
            setattr(target, field, value)

    # 3. 补齐基础资料
    for field in ("email", "mobile", "employee_no", "department", "position"):
        if not getattr(target, field, None) and getattr(source, field, None):
            setattr(target, field, getattr(source, field))

    # 4. 软删源记录
    source.is_deleted = True
    source.updated_by = operator_id
    target.updated_by = operator_id
    await db.commit()

    return {"moved_grants": moved, "deduplicated_grants": deduplicated}


async def unbind_feishu_user(
    db: AsyncSession,
    *,
    user: User,
    operator_id: UUID | None = None,
    delete_account: bool = False,
) -> None:
    """解绑飞书身份。

    - `delete_account=False`：只清空飞书字段，账号本体与角色授权保留；
    - `delete_account=True`：该账号是飞书首次登录自动创建的（auth_source=feishu），
      解绑后没有可用的登录身份，直接软删除并禁用。
    """
    if delete_account:
        user.is_deleted = True
        user.status = "disabled"
    else:
        for field in FEISHU_IDENTITY_FIELDS:
            setattr(user, field, None)
    user.updated_by = operator_id
    await db.commit()


async def reset_password_by_admin(
    db: AsyncSession,
    *,
    user: User,
    password: str | None,
    operator_id: UUID | None = None,
) -> str:
    """管理员为账号设置密码；`password` 为空则随机生成。

    返回本次生成的明文密码（管理员自填时返回空串）—— 随机密码**只在此处返回一次**，
    不落库明文，前端弹窗展示后即不可再查看。两种情况都置 `must_change_password`，
    强制用户首次登录后自行修改。
    """
    plain = (password or "").strip()
    generated = ""
    if not plain:
        generated = generate_random_password()
        plain = generated
    else:
        strength_error = validate_password_strength(plain)
        if strength_error:
            from app.core.exceptions import BadRequestException

            raise BadRequestException(strength_error)

    user.password_hash = hash_password(plain)
    user.password_updated_at = datetime.now(UTC)
    user.must_change_password = True
    user.updated_by = operator_id
    await db.commit()
    return generated


async def change_own_password(
    db: AsyncSession,
    *,
    user: User,
    old_password: str,
    new_password: str,
) -> None:
    """用户自助改密：校验原密码 → 更新哈希 → 清除强制改密标记。

    原密码错误返回 400（不是 401）：前端把 401 当作会话过期会触发登录跳转。
    """
    from app.core.exceptions import BadRequestException

    if not verify_password(old_password, user.password_hash):
        raise BadRequestException("原密码不正确")
    if old_password == new_password:
        raise BadRequestException("新密码不能与原密码相同")

    strength_error = validate_password_strength(new_password)
    if strength_error:
        raise BadRequestException(strength_error)

    user.password_hash = hash_password(new_password)
    user.password_updated_at = datetime.now(UTC)
    user.must_change_password = False
    await db.commit()


async def bootstrap_local_users() -> None:
    """创建引导账号（幂等）。

    **只补建、不覆盖**：账号已存在时，每次启动都不再改动它的密码 / 姓名 / 邮箱 /
    状态 —— 否则用户自己改过的密码会在容器重启后被 `.env` 里的初始值打回，
    「密码只有本人能改」形同虚设；运维在界面上的改名、禁用也会被静默还原。
    确实需要按 `.env` 强制回灌时，显式打开 `BOOTSTRAP_ADMIN_FORCE_RESET=true`。
    """
    settings = get_settings()
    force_reset = settings.BOOTSTRAP_ADMIN_FORCE_RESET
    entries = [
        (
            settings.BOOTSTRAP_ADMIN_USERNAME,
            settings.BOOTSTRAP_ADMIN_PASSWORD,
            settings.BOOTSTRAP_ADMIN_NAME,
            settings.BOOTSTRAP_ADMIN_EMAIL,
        ),
        (
            settings.BOOTSTRAP_USER_USERNAME,
            settings.BOOTSTRAP_USER_PASSWORD,
            settings.BOOTSTRAP_USER_NAME,
            settings.BOOTSTRAP_USER_EMAIL,
        ),
    ]

    async with async_session_factory() as session:
        for username, password, name, email in entries:
            if not username or not password:
                continue
            existing = await _repo.get_by_username(session, username)
            if existing is None:
                await _repo.create(
                    session,
                    username=username,
                    password_hash=hash_password(password),
                    name=name or username,
                    email=email or None,
                    status="active",
                    auth_source="local",
                    # 引导密码是公开的初始值 → 首次登录必须改密
                    must_change_password=True,
                )
                logger.info("Bootstrapped local user: %s", username)
                continue

            if not force_reset:
                # 只补建、不覆盖：账号一旦存在，姓名 / 邮箱 / 状态 / 密码都以库内为准，
                # 避免每次重启把运维在界面上的改动（改名、禁用）静默打回。
                continue

            if not verify_password(password, existing.password_hash):
                existing.password_hash = hash_password(password)
                existing.must_change_password = True
                logger.warning("Bootstrapped local user password force-reset: %s", username)

            existing.name = name or existing.name
            existing.email = email or existing.email
            existing.status = "active"
            existing.auth_source = existing.auth_source or "local"

        # 未配置引导管理员时才落「登录关闭模式」的占位管理员，避免与引导账号并存出两个账号
        if not (settings.BOOTSTRAP_ADMIN_USERNAME and settings.BOOTSTRAP_ADMIN_PASSWORD):
            await get_or_create_system_admin(session)
        await session.commit()


async def get_or_create_system_admin(db: AsyncSession) -> User:
    """Return the platform default administrator used when login is disabled."""
    user = await _repo.get_by_username_including_deleted(db, SYSTEM_ADMIN_USERNAME)
    if user is None:
        user = await _repo.create(
            db,
            username=SYSTEM_ADMIN_USERNAME,
            name=SYSTEM_ADMIN_NAME,
            status="active",
            auth_source="local",
        )
        logger.info("Created default platform administrator: %s", SYSTEM_ADMIN_USERNAME)
        return user

    changed = False
    if user.name != SYSTEM_ADMIN_NAME:
        user.name = SYSTEM_ADMIN_NAME
        changed = True
    if user.status != "active":
        user.status = "active"
        changed = True
    if user.auth_source != "local":
        user.auth_source = "local"
        changed = True
    if user.is_deleted:
        user.is_deleted = False
        changed = True

    if changed:
        await db.flush()
    return user


def generate_state_token() -> str:
    """Generate a short-lived state token for CSRF protection."""
    import secrets

    settings = get_settings()
    nonce = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    payload = {
        "nonce": nonce,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def validate_state_token(state: str) -> bool:
    """Validate a state token. Returns True if valid and not expired."""
    settings = get_settings()
    try:
        jwt.decode(state, settings.SECRET_KEY, algorithms=["HS256"])
        return True
    except jwt.InvalidTokenError:
        return False
