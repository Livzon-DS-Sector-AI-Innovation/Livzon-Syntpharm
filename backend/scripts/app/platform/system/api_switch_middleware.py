"""API 启停开关中间件：命中禁用清单的请求直接 403。

判定完全在内存（api_switch_service 的禁用集合 + 模板匹配），无 DB 查询开销；
无禁用项时走快路径直接放行。
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.platform.system import api_switch_service

logger = logging.getLogger(__name__)


class ApiSwitchMiddleware(BaseHTTPMiddleware):
    """被管理员禁用的接口一律 403（保护名单除外，见 api_switch_service）。"""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if not api_switch_service.has_disabled():
            return await call_next(request)

        blocked, reason = api_switch_service.match_disabled(request.method, request.url.path)
        if blocked:
            logger.warning(
                "api_switch_blocked method=%s path=%s",
                request.method,
                request.url.path,
            )
            message = f"该接口已被管理员禁用：{reason}" if reason else "该接口已被管理员禁用"
            return JSONResponse(status_code=403, content={"code": 403, "message": message})

        return await call_next(request)
