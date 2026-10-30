"""抢单 API 路由."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import AppException, ForbiddenException
from app.core.response import DataResponse
from app.core.tasks import spawn_task
from app.modules.equipment import service
from app.modules.equipment.schemas import WorkOrderResponse
from app.platform.integrations.feishu.contact import is_department_member
from app.platform.integrations.feishu.message import send_claim_notification

router = APIRouter()


@router.put("/{work_order_id}/claim", summary="抢单（维修人员自主接单）")
async def claim_work_order(
    work_order_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:work-order:update")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DataResponse[WorkOrderResponse]:
    assert current_user is not None

    dept_id = settings.feishu.platform.equipment_dept_id
    if not dept_id:
        raise AppException(message="设备部未配置")

    feishu_id = current_user.feishu_user_id or ""
    if not feishu_id:
        raise ForbiddenException(message="用户未关联飞书账号")

    is_member = await is_department_member(feishu_id, dept_id)
    if not is_member:
        raise ForbiddenException(message="只有设备部成员才能接单")

    wo = await service.claim_work_order(db, work_order_id, current_user.id)

    # 通知失败不应影响接单结果；用 spawn_task 包装后异常会进日志（ensure_future 只是静默丢弃）
    spawn_task(
        send_claim_notification(wo.work_order_no, current_user.name),
        name=f"claim-notify-{wo.work_order_no}",
    )

    resp = WorkOrderResponse.model_validate(wo)
    if wo.reporter:
        resp.reporter_name = wo.reporter.name
    if wo.assignee:
        resp.assignee_name = wo.assignee.name
    return DataResponse[WorkOrderResponse](data=resp)
