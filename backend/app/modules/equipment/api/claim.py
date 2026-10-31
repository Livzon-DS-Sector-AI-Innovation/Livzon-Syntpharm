"""抢单 API 路由."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import AppException, ForbiddenException
from app.core.jobs import submit_job_safe
from app.core.response import DataResponse
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

    # 通知失败不应影响接单结果：投递到任务队列（状态可查、失败留记录），登记失败只记日志
    work_order_no = wo.work_order_no
    claimer_name = current_user.name

    async def _notify_claimer(_job_id: uuid.UUID) -> dict[str, str]:
        await send_claim_notification(work_order_no, claimer_name)
        return {"work_order_no": work_order_no}

    await submit_job_safe(f"equipment.claim-notify-{work_order_no}", _notify_claimer)

    resp = WorkOrderResponse.model_validate(wo)
    if wo.reporter:
        resp.reporter_name = wo.reporter.name
    if wo.assignee:
        resp.assignee_name = wo.assignee.name
    return DataResponse[WorkOrderResponse](data=resp)
