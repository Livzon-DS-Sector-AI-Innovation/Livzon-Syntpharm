from fastapi import APIRouter, Depends

from app.platform.identity.deps import require_current_user
from app.platform.identity.models import User
from app.shared.module_registry import ModuleDefinition


def create_module_router(module: ModuleDefinition) -> APIRouter:
    router = APIRouter()

    # 模块信息是静态元数据（名称/路径/描述），只要求登录态。
    # 不挂 require_permission：该依赖是端点级立即生效，挂粗码会让未灰度模块的
    # 无权限用户立刻 403（environment 等页面在用）。中间件兜底只要求「已登记绑定」，
    # 绑定语义登记在 registry（research 绑 research:module:read），与菜单可见性对齐。
    @router.get("/", summary=f"{module.name}模块信息")
    async def read_module(user: User = Depends(require_current_user)) -> dict[str, str]:
        return module.as_dict()

    return router
