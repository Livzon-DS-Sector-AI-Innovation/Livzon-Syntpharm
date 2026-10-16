"""菜单栏管理 API（显示/隐藏 + 排列权重 + 权限绑定 + 自定义菜单项）。

挂载前缀：/api/v1/system（见 api/router.py）。
权限：读 `platform:ops:read`、写 `platform:ops:manage`（复用系统运维权限码，不新增）。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.platform.audit.service import record_audit_log
from app.platform.system import menu_service
from app.platform.system.menu_schemas import (
    MenuConfigData,
    MenuConfigResponse,
    MenuConfigSaveRequest,
    MenuConfigSaveResponse,
)

router = APIRouter(tags=["菜单管理"])


@router.get("/menus/config", response_model=MenuConfigResponse, summary="读取菜单栏配置")
async def get_menu_config(
    current_user: RequiredUser,
) -> MenuConfigResponse:
    """返回菜单的显隐/权重/权限覆盖配置与自定义菜单项（未配置 = 空，前端按代码默认渲染）。

    **只要求已登录**（不做权限码校验）：每个用户的导航渲染都要读这份配置，
    若要求 `platform:ops:read`，普通用户读不到 → 菜单配置对他们不生效。
    写操作（PUT）仍要求 `platform:ops:manage`。
    """
    data = await menu_service.load_menu_config()
    return MenuConfigResponse(data=MenuConfigData(**data))


@router.put("/menus/config", response_model=MenuConfigSaveResponse, summary="保存菜单栏配置")
async def put_menu_config(
    payload: MenuConfigSaveRequest,
    ctx: PermissionContext = Depends(require_permission("platform:ops:manage")),
    db: AsyncSession = Depends(get_db),
) -> MenuConfigSaveResponse:
    """整体保存菜单配置（护栏校验不通过返回 400）。"""
    items = {key: value.model_dump(exclude_none=True) for key, value in payload.items.items()}
    custom = [item.model_dump() for item in payload.custom]

    menu_service.validate_config(items, custom)
    data = await menu_service.save_menu_config(items=items, custom=custom, updated_by=ctx.user.id)

    await record_audit_log(
        db,
        user=ctx.user,
        action="menu.config.save",
        resource_type="menu",
        new_value={"items": items, "custom": custom},
    )
    await db.commit()

    return MenuConfigSaveResponse(data=MenuConfigData(**data))
