"""维修人员 API 路由."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import success_response
from app.modules.equipment.models.personnel import EquipmentPersonnel
from app.platform.identity import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/maintainers", summary="获取设备模块维修人员列表")
async def list_maintainers(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:maintenance-staff:read")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """从人员配置中获取所有在岗人员，供工单指派维修人时选择。"""
    result = await db.execute(
        select(EquipmentPersonnel, User.username)
        .outerjoin(User, User.id == EquipmentPersonnel.user_id)
        .where(
            EquipmentPersonnel.is_deleted == False,  # noqa: E712
            EquipmentPersonnel.is_active == True,  # noqa: E712
            EquipmentPersonnel.user_id.isnot(None),
        )
        .order_by(EquipmentPersonnel.name)
    )
    rows = result.all()

    maintainers = [
        {
            "user_id": str(p.user_id),
            "name": p.name,
            # 选人下拉用「姓名（账号）」展示，重名时可区分
            "username": username or "",
            "employee_no": p.employee_no or "",
            "department_id": p.department or "",
        }
        for p, username in rows
    ]

    return success_response(data=maintainers)


@router.get("/all-users", summary="获取全体员工列表")
async def list_all_users(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:maintenance-staff:read")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """返回所有本地用户，供工单责任人选择。"""
    result = await db.execute(
        select(User.id, User.name, User.username, User.employee_no)
        .where(User.is_deleted == False)  # noqa: E712
        .order_by(User.name)
    )
    users = [
        {
            "user_id": str(row.id),
            "name": row.name,
            "username": row.username or "",
            "employee_no": row.employee_no or "",
        }
        for row in result.all()
    ]
    return success_response(data=users)
