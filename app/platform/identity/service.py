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
from uuid import UUID

import jwt
from fastapi import HTTPException, status
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
        (
            "Livzon 助手飞书密钥加解密失败："
            f"{exc}。请检查后端 ENCRYPTION_KEY 配置是否与保存配置时一致。"
        ),
    )


def hash_password(password: str) -> str:
    """Hash a local-account password using PBKDF2-SHA256."""
    salt = secrets.token_bytes(16)
    digest = pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${_PASSWORD_ITERATIONS}$"
        f"{salt.hex()}${digest.hex()}"
    )


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
        card_callback_verification_token_configured=bool(
            config.card_callback_verification_token
        ),
        card_callback_verification_token_masked=mask_secret(
            config.card_callback_verification_token or ""
        ),
        card_callback_encrypt_key_configured=bool(
            config.encrypted_card_callback_encrypt_key
        ),
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


async def save_livzon_feishu_config(
    db: AsyncSession, payload: FeishuConfigUpsert
) -> FeishuConfigResponse:
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

    app_id = (payload.app_id if payload else None) or (
        stored.app_id if stored else None
    ) or settings.FEISHU_APP_ID
    encrypted_secret = stored.encrypted_app_secret if stored else ""
    try:
        app_secret = (
            payload.app_secret
            if payload and payload.app_secret
            else decrypt_secret(encrypted_secret)
            if encrypted_secret
            else settings.FEISHU_APP_SECRET
        )
    except RuntimeError as exc:
        raise _secret_runtime_error(exc) from exc
    root_id = (
        (payload.sync_root_department_id if payload else None)
        or (stored.sync_root_department_id if stored else None)
        or settings.FEISHU_SYNC_ROOT_DEPT_ID
        or "0"
    )
    member_id = (
        (payload.sync_member_department_id if payload else None)
        or (stored.sync_member_department_id if stored else None)
        or settings.FEISHU_SYNC_MEMBER_DEPT_ID
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
    departments: list[dict] = []
    users: list[dict] = []
    scope: dict = {}
    stored = await _feishu_config_repo.get_active(db)

    try:
        app_id, app_secret, root_id, member_id = await _effective_feishu_credentials(
            db, payload
        )
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
                suggestion=(
                    "请确认 App ID / App Secret 正确，且应用已发布或处于可调用状态。"
                ),
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
                status="ok"
                if scope_department_count or scope_user_count or scope_group_count
                else "warning",
                message=(
                    "当前应用通讯录授权范围："
                    f"部门 {scope_department_count} 个，"
                    f"用户 {scope_user_count} 名，"
                    f"用户组 {scope_group_count} 个。"
                ),
                suggestion=None
                if scope_department_count or scope_user_count or scope_group_count
                else (
                    "飞书开放平台的权限开通后，还需要在“通讯录权限范围”"
                    "中授权可访问的部门或成员。"
                ),
            )
        )
    except Exception as exc:
        steps.append(
            FeishuDiagnosticStep(
                name="通讯录授权范围",
                status="warning",
                message=f"读取通讯录授权范围失败：{exc}",
                suggestion=(
                    "请确认已开通 contact:scope:readonly，或在飞书开放平台检查"
                    "通讯录权限范围是否已发布生效。"
                ),
            )
        )

    try:
        departments = await get_all_departments(
            root_department_id=root_id,
            app_id=app_id,
            app_secret=app_secret,
            tenant_access_token=token,
        )
        steps.append(
            FeishuDiagnosticStep(
                name="部门列表",
                status="ok" if departments else "warning",
                message=(
                    f"读取到 {len(departments)} 个部门。"
                    if departments
                    else "部门 API 调用成功，但未读取到部门数据。"
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
    departments_with_members = (
        dept.get("department_id", "")
        for dept in departments
        if dept.get("member_count")
    )
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
                users = await find_users_by_department(
                    sample_department_id,
                    app_id=app_id,
                    app_secret=app_secret,
                    tenant_access_token=token,
                )
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
                        else (
                            "已尝试部门 "
                            f"{', '.join(tried_ids[:5])}，API 调用成功，"
                            "但未读取到用户。"
                        )
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
                    suggestion=(
                        "请开通 contact:user.base:readonly，"
                        "并确认应用通讯录权限范围包含目标部门。"
                    ),
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
                    suggestion=None
                    if has_department_ids
                    else "请开通 contact:user.department:readonly。",
                ),
                FeishuDiagnosticStep(
                    name="用户手机号",
                    status="ok" if has_mobile else "warning",
                    message="已返回至少一名用户手机号。"
                    if has_mobile
                    else "用户可读取，但未返回手机号。",
                    suggestion=None
                    if has_mobile
                    else (
                        "请开通 contact:user.phone:readonly，"
                        "并确认通讯录权限范围包含手机号字段。"
                    ),
                ),
                FeishuDiagnosticStep(
                    name="用户邮箱",
                    status="ok" if has_email else "warning",
                    message="已返回至少一名用户邮箱。"
                    if has_email
                    else "用户可读取，但未返回邮箱。",
                    suggestion=None
                    if has_email
                    else (
                        "请开通 contact:user.email:readonly，"
                        "并确认通讯录权限范围包含邮箱字段。"
                    ),
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


async def run_livzon_feishu_sync_all(db: AsyncSession) -> dict:
    from app.platform.integrations.feishu.contact import get_contact_scope
    from app.platform.integrations.feishu.sync import (
        sync_departments,
        sync_members,
        sync_users_by_ids,
    )

    config = await _feishu_config_repo.get_active(db)
    app_id, app_secret, root_id, member_id = await _effective_feishu_credentials(db)

    scope: dict = {}
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

    dept_results: list[dict] = []
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

    member_results: list[dict] = []
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
    nested_member_errors = [
        str(error)
        for result in member_results
        for error in result.get("errors", [])
    ]
    all_errors = dept_errors + member_errors + nested_member_errors

    if not dept_results and not member_results and not direct_user_count:
        message = (
            "同步失败：当前 Livzon 助手飞书应用没有可同步的通讯录数据。"
            "请检查通讯录权限范围是否包含目标部门或用户。"
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
    sync_message = (
        f"同步完成：部门 {dept_count} 个，"
        f"部门用户 {member_count} 名，直接授权用户 {direct_user_count} 名。"
    )
    if sync_status == "warning":
        sync_message = (
            f"{sync_message} 部分部门同步失败："
            f"{'; '.join(all_errors)}"
        )
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


def _empty_message_result(user_id: UUID, message: str) -> dict:
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


def _normalize_card_actions(actions: list[dict] | None) -> list[dict[str, str]]:
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
) -> dict:
    from app.platform.integrations.feishu.im import send_feishu_message
    from app.platform.integrations.feishu.utils import get_tenant_access_token

    app_id, app_secret = await _active_livzon_feishu_credentials(db)
    token = await get_tenant_access_token(
        app_id,
        app_secret,
        cache_key=f"livzon-assistant:{app_id}",
    )

    results: list[dict] = []
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
    actions: list[dict] | None,
    business_ref: dict | None,
) -> dict:
    from app.platform.integrations.feishu.im import (
        build_callback_card_content,
        send_feishu_message,
    )
    from app.platform.integrations.feishu.utils import get_tenant_access_token

    settings = get_settings()
    config = await _feishu_config_repo.get_active(db)
    if config is None or (
        not config.card_callback_verification_token
        and not settings.LIVZON_FEISHU_CARD_CALLBACK_WS_ENABLED
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
    results: list[dict] = []
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
) -> dict:
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
) -> dict:
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
    actions: list[dict] | None = None,
    business_ref: dict | None = None,
    header_template: str = "blue",
    message_form: str = "auto",
) -> dict:
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
    if not encrypt_key or not timestamp or not nonce or not signature:
        return True
    raw = f"{timestamp}{nonce}{encrypt_key}".encode() + raw_body
    expected = hashlib.sha256(raw).hexdigest()
    return hmac.compare_digest(expected, signature)


def _callback_payload_token(payload: dict) -> str | None:
    token = payload.get("token")
    if isinstance(token, str):
        return token
    header = payload.get("header")
    if isinstance(header, dict) and isinstance(header.get("token"), str):
        return header["token"]
    return None


def _extract_callback_action(
    payload: dict,
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
    payload: dict,
    raw_body: bytes,
    timestamp: str | None = None,
    nonce: str | None = None,
    signature: str | None = None,
) -> dict:
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
    payload: dict,
) -> dict:
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
    avatar_url = info.get("avatar_url") or info.get("avatar_middle")
    avatar_thumb = info.get("avatar_thumb")
    avatar_middle = info.get("avatar_middle")
    avatar_big = info.get("avatar_big")
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
            role="admin"
            if _matches_admin_whitelist(
                User(
                    name=name,
                    feishu_user_id=user_id,
                    feishu_open_id=open_id,
                    email=email,
                    enterprise_email=enterprise_email,
                    mobile=mobile,
                ),
                get_settings().SSO_ADMIN_IDENTIFIERS,
            )
            else "user",
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
            user.role = "admin"
        logger.info("Updated user: %s (open_id=%s)", user.name, open_id)

    if user.status == "disabled":
        raise PermissionError("User account is disabled")
    user.last_login_at = datetime.now(UTC)
    await db.commit()

    # 4. Generate JWT
    token = generate_jwt(user)
    return user, token


def generate_jwt(user: User) -> str:
    """Generate a JWT token for the given user."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "open_id": user.feishu_open_id,
        "name": user.name,
        "role": user.role,
        "auth_source": user.auth_source,
        "iat": now,
        "exp": now + timedelta(seconds=settings.JWT_EXPIRE_SECONDS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


async def authenticate_local_user(
    db: AsyncSession, *, username: str, password: str
) -> tuple[User, str]:
    user = await _repo.get_by_login_identifier(db, username)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    if user.status == "disabled":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已禁用")
    user.last_login_at = datetime.now(UTC)
    await db.flush()
    return user, generate_jwt(user)


async def bootstrap_local_users() -> None:
    settings = get_settings()
    entries = [
        (
            settings.BOOTSTRAP_ADMIN_USERNAME,
            settings.BOOTSTRAP_ADMIN_PASSWORD,
            settings.BOOTSTRAP_ADMIN_NAME,
            settings.BOOTSTRAP_ADMIN_EMAIL,
            "admin",
        ),
        (
            settings.BOOTSTRAP_USER_USERNAME,
            settings.BOOTSTRAP_USER_PASSWORD,
            settings.BOOTSTRAP_USER_NAME,
            settings.BOOTSTRAP_USER_EMAIL,
            "user",
        ),
    ]

    async with async_session_factory() as session:
        for username, password, name, email, role in entries:
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
                    role=role,
                    status="active",
                    auth_source="local",
                )
                logger.info("Bootstrapped %s local user: %s", role, username)
                continue

            existing.password_hash = hash_password(password)
            existing.name = name or existing.name
            existing.email = email or existing.email
            existing.role = role
            existing.status = "active"
            existing.auth_source = existing.auth_source or "local"

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
            role="admin",
            status="active",
            auth_source="local",
        )
        logger.info("Created default platform administrator: %s", SYSTEM_ADMIN_USERNAME)
        return user

    changed = False
    if user.name != SYSTEM_ADMIN_NAME:
        user.name = SYSTEM_ADMIN_NAME
        changed = True
    if user.role != "admin":
        user.role = "admin"
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
