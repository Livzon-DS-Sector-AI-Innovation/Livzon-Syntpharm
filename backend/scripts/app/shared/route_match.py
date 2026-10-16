"""路由模板匹配工具（供中间件把「实际请求路径」匹配到「路由模板」）。

FastAPI 新版本用 `_IncludedRouter` 懒包装 include_router 的路由，
`app.routes` 不再扁平包含全部接口，因此中间件改用「按清单模板匹配」，
只遍历少量登记项（禁用清单 / 权限绑定表），零额外开销。
"""

import re

_TEMPLATE_PARAM = re.compile(r"\{[^}]+\}")


def template_matches(template: str, path: str) -> bool:
    """判断实际请求路径是否匹配路由模板。

    `/api/v1/quality/deviations/{id}` 可匹配 `/api/v1/quality/deviations/abc-123`。
    """
    if template == path:
        return True
    if "{" not in template:
        return False
    parts = _TEMPLATE_PARAM.split(template)
    pattern = "[^/]+".join(re.escape(part) for part in parts)
    return re.fullmatch(pattern, path) is not None
