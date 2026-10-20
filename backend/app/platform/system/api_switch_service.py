"""API 启停开关服务（运维应急开关）。

用途：某个接口出问题需要临时下线（无需发版）时，按「方法 + 路由」禁用。
存储：`core.module_settings`（module=system, key=DISABLED_API_ROUTES, JSON 数组），
      启动时加载进内存，请求路径上 O(1) 判定，不查库。

安全边界：保护名单内的接口不可禁用（健康检查、登录、系统运维自身），防把自己锁死。
"""

import json
import logging
from dataclasses import dataclass

from sqlalchemy import select

# 确保 identity.users 表注册（ModuleSetting 的 created_by/updated_by 外键目标），
# 否则单独 import 本模块时 FK 解析报 NoReferencedTableError
import app.platform.identity.models  # noqa: F401
from app.core.config_model import ModuleSetting
from app.core.database import async_session_factory

logger = logging.getLogger(__name__)

SETTING_MODULE = "system"
SETTING_KEY = "DISABLED_API_ROUTES"
SETTING_DESCRIPTION = "被禁用的 API 路由（系统运维开关，JSON 数组）"

# 不可禁用的路径前缀（防锁死：健康检查 / 登录 / 运维自身）
PROTECTED_PREFIXES: tuple[str, ...] = (
    "/health",
    "/api/v1/identity/auth",
    "/api/v1/system",
)

# (method, route_template) -> 禁用原因
_DISABLED: dict[tuple[str, str], str | None] = {}


@dataclass
class ApiRouteItem:
    method: str
    route: str
    summary: str
    tags: list[str]
    disabled: bool
    reason: str | None
    protected: bool


def is_protected_route(route: str) -> bool:
    """保护名单：健康检查、登录、系统运维接口不可禁用。"""
    return any(route == prefix or route.startswith(prefix + "/") for prefix in PROTECTED_PREFIXES)


def is_disabled(method: str, route: str) -> tuple[bool, str | None]:
    """内存判定（O(1)）：返回 (是否禁用, 禁用原因)。"""
    key = (method.upper(), route)
    return key in _DISABLED, _DISABLED.get(key)


def has_disabled() -> bool:
    """是否存在任何禁用项（中间件快路径判断，避免无谓的路由匹配）。"""
    return bool(_DISABLED)


def disabled_count() -> int:
    return len(_DISABLED)


# ── 加载 / 持久化 ─────────────────────────────────────────────────


async def load_switches() -> None:
    """启动时加载禁用清单到内存（失败只告警，不影响启动）。"""
    async with async_session_factory() as db:
        result = await db.execute(
            select(ModuleSetting).where(
                ModuleSetting.module == SETTING_MODULE,
                ModuleSetting.key == SETTING_KEY,
                ModuleSetting.is_deleted == False,  # noqa: E712
            )
        )
        setting = result.scalar_one_or_none()

    _DISABLED.clear()
    if setting and setting.value:
        try:
            for item in json.loads(setting.value):
                method = str(item.get("method", "")).upper()
                route = str(item.get("route", ""))
                if method and route:
                    _DISABLED[(method, route)] = item.get("reason")
        except (json.JSONDecodeError, AttributeError, TypeError):
            logger.exception("禁用清单解析失败，按空清单处理")

    logger.info("API 开关已加载：%d 条禁用", len(_DISABLED))


async def _persist(actor_id) -> None:  # noqa: ANN001 - uuid.UUID | None
    payload = [
        {"method": method, "route": route, "reason": reason} for (method, route), reason in sorted(_DISABLED.items())
    ]
    value = json.dumps(payload, ensure_ascii=False)

    async with async_session_factory() as db:
        result = await db.execute(
            select(ModuleSetting).where(
                ModuleSetting.module == SETTING_MODULE,
                ModuleSetting.key == SETTING_KEY,
                ModuleSetting.is_deleted == False,  # noqa: E712
            )
        )
        setting = result.scalar_one_or_none()
        if setting is None:
            db.add(
                ModuleSetting(
                    module=SETTING_MODULE,
                    key=SETTING_KEY,
                    value=value,
                    value_type="json",
                    description=SETTING_DESCRIPTION,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )
        else:
            setting.value = value
            setting.updated_by = actor_id
        await db.commit()


# ── 清单 / 变更 ───────────────────────────────────────────────────


_HTTP_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")


def list_api_routes(app) -> list[ApiRouteItem]:  # noqa: ANN001 - fastapi.FastAPI
    """从 OpenAPI schema 导出全部接口（自动跟随代码，无需维护清单）。

    不用 `app.routes`：FastAPI 新版用 _IncludedRouter 懒包装 include_router 的路由，
    app.routes 不再扁平包含全部接口；OpenAPI schema 是完整且稳定的来源。
    """
    schema = app.openapi()
    items: list[ApiRouteItem] = []
    for path, methods in (schema.get("paths") or {}).items():
        for method, operation in methods.items():
            method_upper = method.upper()
            if method_upper not in _HTTP_METHODS:
                continue
            blocked, reason = is_disabled(method_upper, path)
            items.append(
                ApiRouteItem(
                    method=method_upper,
                    route=path,
                    summary=str(operation.get("summary") or ""),
                    tags=[str(tag) for tag in (operation.get("tags") or [])],
                    disabled=blocked,
                    reason=reason,
                    protected=is_protected_route(path),
                )
            )
    return items


def match_disabled(method: str, path: str) -> tuple[bool, str | None]:
    """把实际请求路径与禁用清单做模板匹配（只遍历禁用项，通常 0~几条）。"""
    from app.shared.route_match import template_matches

    method = method.upper()
    for (disabled_method, template), reason in _DISABLED.items():
        if disabled_method == method and template_matches(template, path):
            return True, reason
    return False, None


async def set_switch(
    method: str,
    route: str,
    enabled: bool,
    reason: str | None,
    actor_id,  # noqa: ANN001 - uuid.UUID
) -> None:
    """启用 / 禁用某接口：更新内存 + 持久化 + 写审计。"""
    method = method.upper()
    if not enabled and is_protected_route(route):
        raise ValueError("该接口属于保护名单（健康检查 / 登录 / 系统运维），不允许禁用")

    key = (method, route)
    if enabled:
        _DISABLED.pop(key, None)
    else:
        _DISABLED[key] = reason or None

    await _persist(actor_id)

    # 审计（同事务不可行——_persist 自开 session，这里独立记录）
    try:
        from app.platform.audit.service import record_audit_log

        async with async_session_factory() as db:
            await record_audit_log(
                db,
                user_id=actor_id,
                action="api_switch_enable" if enabled else "api_switch_disable",
                resource_type="api_route",
                extra={"method": method, "route": route, "reason": reason},
            )
            await db.commit()
    except Exception:  # noqa: BLE001 - 审计失败不影响开关生效
        logger.exception("API 开关审计写入失败")
