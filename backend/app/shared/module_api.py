from typing import Any

from fastapi import APIRouter, Depends

from app.core.deps import require_current_user
from app.shared.module_registry import ModuleDefinition


def create_module_router(module: ModuleDefinition) -> APIRouter:
    router = APIRouter()

    # 模块信息是静态元数据（名称/路径/描述），只要求登录态。
    # 不挂 require_permission：该依赖是端点级立即生效，挂粗码会让未灰度模块的
    # 无权限用户立刻 403（environment 等页面在用）。中间件兜底只要求「已登记绑定」，
    # 绑定语义登记在 registry（research 绑 research:module:read），与菜单可见性对齐。
    #
    # 依赖从 `app.core.deps` 门面导入、返回类型用 `Any`，而不是直接 import
    # `platform.identity.deps/models`：`platform.identity.models` 又依赖 `shared.base_model`，
    # 直接 import 会让 shared ↔ platform.identity 形成包级环。
    @router.get("/", summary=f"{module.name}模块信息")
    async def read_module(user: Any = Depends(require_current_user)) -> dict[str, str]:
        return module.as_dict()

    return router
