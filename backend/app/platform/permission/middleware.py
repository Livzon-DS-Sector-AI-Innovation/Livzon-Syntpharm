"""接口精确绑定兜底中间件（fail-closed）。

每个受保护动作都登记「方法 + 路由模板」到 registry.API_BINDINGS，
未登记 → 一律 403。这是防止「新加了接口、忘了加权限依赖」的兜底。

判定完全基于内存中的代码注册表（registry 是唯一权威），不查 DB，零额外开销。
注意：不用 `app.routes` 做路由匹配——FastAPI 新版用 _IncludedRouter 懒包装
include_router 的路由，app.routes 不再扁平包含全部接口；改为按绑定表的
路由模板做匹配（登记项数量少，遍历成本可忽略）。
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.platform.permission.registry import (
    BINDINGS_BY_ROUTE,
    EXEMPT_ROUTES,
    ApiBindingDef,
    is_protected_route,
)
from app.shared.route_match import template_matches

logger = logging.getLogger(__name__)


def _find_binding(method: str, path: str) -> ApiBindingDef | None:
    """按「方法 + 实际路径」匹配绑定登记项。"""
    method = method.upper()
    for (binding_method, template), binding in BINDINGS_BY_ROUTE.items():
        if binding_method == method and template_matches(template, path):
            return binding
    return None


def _is_exempt(method: str, path: str) -> bool:
    """登录入口 / 当前用户自取类接口：豁免绑定兜底。

    这类接口不可能持有权限码（登录入口）或只要求已登录（/me），
    若不豁免，开启兜底后登录链路会整体 403。
    """
    method = method.upper()
    return any(
        exempt_method == method and template_matches(template, path) for exempt_method, template in EXEMPT_ROUTES
    )


class PermissionBindingMiddleware(BaseHTTPMiddleware):
    """接口绑定兜底：受保护前缀下，未登记绑定的请求直接 403。"""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        settings = get_settings()
        if not settings.PERMISSION_ENFORCE_ENABLED:
            return await call_next(request)

        path = request.url.path
        if not is_protected_route(path):
            return await call_next(request)

        binding = _find_binding(request.method, path)
        if binding is None and not _is_exempt(request.method, path):
            logger.warning(
                "permission_binding_missing method=%s path=%s",
                request.method,
                path,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "code": 403,
                    "message": "接口未登记权限绑定，已拒绝",
                    "detail": f"{request.method} {path}",
                },
            )

        return await call_next(request)
