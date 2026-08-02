"""Safety API — scheduled_tasks endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.exceptions import NotFoundException
from app.core.response import ApiResponse, paginated_response, success_response
from app.modules.safety.schemas import (
    CardPreviewRequest,
    ScheduledTaskCreate,
    ScheduledTaskLogResponse,
    ScheduledTaskResponse,
    ScheduledTaskUpdate,
)
from app.modules.safety.service import (
    ScheduledTaskService,
)

scheduled_tasks_router = APIRouter()


@scheduled_tasks_router.get(
    "/scheduled-tasks/data-source-options", response_model=ApiResponse, summary="获取可用数据来源选项"
)
async def get_data_source_options(current_user: RequiredUser) -> Any:
    """获取可用的数据来源列表（供前端下拉选择）"""
    options = ScheduledTaskService.get_data_source_options()
    return success_response(data=options)


@scheduled_tasks_router.post("/scheduled-tasks/preview-card", response_model=ApiResponse, summary="预览消息卡片")
async def preview_card(
    data: CardPreviewRequest,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """预览消息卡片渲染效果"""
    service = ScheduledTaskService(db)
    result = await service.preview_card(data)
    return success_response(data=result)


@scheduled_tasks_router.get("/scheduled-tasks/feishu-chats", response_model=ApiResponse, summary="获取飞书群聊列表")
async def get_feishu_chats(
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取可选的飞书群聊列表（从缓存或配置中读取）"""
    from app.core.config import get_settings

    settings = get_settings()
    chats: list[dict[str, Any]] = []
    # Include configured chats
    if settings.feishu.platform.equipment_chat_id:
        chats.append(
            {
                "chat_id": settings.feishu.platform.equipment_chat_id,
                "name": "设备管理群",
            }
        )
    if settings.feishu.platform.safety_chat_id:
        chats.append(
            {
                "chat_id": settings.feishu.platform.safety_chat_id,
                "name": "安全模块功能测试群",
            }
        )
    return success_response(data=chats)


@scheduled_tasks_router.get("/scheduled-tasks", response_model=ApiResponse, summary="获取定时任务列表")
async def get_scheduled_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    is_enabled: bool | None = None,
    search: str | None = None,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取定时任务列表（分页）"""
    service = ScheduledTaskService(db)
    skip = (page - 1) * page_size
    items, total = await service.get_tasks(skip, page_size, is_enabled, search)
    return paginated_response(
        data=[ScheduledTaskResponse.model_validate(t) for t in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@scheduled_tasks_router.post("/scheduled-tasks", response_model=ApiResponse, summary="创建定时任务")
async def create_scheduled_task(
    data: ScheduledTaskCreate,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """创建新的定时任务"""
    service = ScheduledTaskService(db)
    task = await service.create_task(data)
    await db.commit()
    return success_response(data=ScheduledTaskResponse.model_validate(task))


@scheduled_tasks_router.get("/scheduled-tasks/{task_id}", response_model=ApiResponse, summary="获取定时任务详情")
async def get_scheduled_task(
    task_id: uuid.UUID,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取单个定时任务详情"""
    service = ScheduledTaskService(db)
    task = await service.get_task(task_id)
    if not task:
        raise NotFoundException(resource="定时任务")
    return success_response(data=ScheduledTaskResponse.model_validate(task))


@scheduled_tasks_router.put("/scheduled-tasks/{task_id}", response_model=ApiResponse, summary="更新定时任务")
async def update_scheduled_task(
    task_id: uuid.UUID,
    data: ScheduledTaskUpdate,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """更新定时任务配置"""
    service = ScheduledTaskService(db)
    task = await service.update_task(task_id, data)
    if not task:
        raise NotFoundException(resource="定时任务")
    await db.commit()
    return success_response(data=ScheduledTaskResponse.model_validate(task))


@scheduled_tasks_router.delete("/scheduled-tasks/{task_id}", response_model=ApiResponse, summary="删除定时任务")
async def delete_scheduled_task(
    task_id: uuid.UUID,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """删除定时任务（软删除）"""
    service = ScheduledTaskService(db)
    ok = await service.delete_task(task_id)
    if not ok:
        raise NotFoundException(resource="定时任务")
    await db.commit()
    return success_response(message="删除成功")


@scheduled_tasks_router.post(
    "/scheduled-tasks/{task_id}/toggle", response_model=ApiResponse, summary="启用/禁用定时任务"
)
async def toggle_scheduled_task(
    task_id: uuid.UUID,
    enabled: bool = Query(..., description="是否启用"),
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """切换定时任务的启用/禁用状态"""
    service = ScheduledTaskService(db)
    task = await service.toggle_task(task_id, enabled)
    if not task:
        raise NotFoundException(resource="定时任务")
    await db.commit()
    return success_response(data=ScheduledTaskResponse.model_validate(task))


@scheduled_tasks_router.post("/scheduled-tasks/{task_id}/run", response_model=ApiResponse, summary="手动执行定时任务")
async def run_scheduled_task_now(
    task_id: uuid.UUID,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """立即手动执行一次定时任务"""
    service = ScheduledTaskService(db)
    log = await service.run_task_now(task_id)
    if not log:
        raise NotFoundException(resource="定时任务")
    await db.commit()
    return success_response(data=ScheduledTaskLogResponse.model_validate(log))


@scheduled_tasks_router.get(
    "/scheduled-tasks/{task_id}/logs", response_model=ApiResponse, summary="获取定时任务执行日志"
)
async def get_scheduled_task_logs(
    task_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取定时任务的执行日志列表"""
    service = ScheduledTaskService(db)
    skip = (page - 1) * page_size
    logs, total = await service.get_logs(task_id, skip, page_size)
    return paginated_response(
        data=[ScheduledTaskLogResponse.model_validate(log) for log in logs],
        page=page,
        page_size=page_size,
        total=total,
    )


# ── 安全模块飞书 WebSocket 管理 ──


@scheduled_tasks_router.post("/feishu/ws/restart", response_model=ApiResponse, summary="手动恢复飞书 WebSocket 连接")
async def restart_feishu_ws(
    current_user: RequiredUser = None,
) -> Any:
    """WS 因重试次数耗尽（3 次）自动停止后，手动重新建立连接。

    无需传参，调用即重置重试计数并创建新的 WS 任务。
    返回当前已注册的事件类型列表。
    """
    from app.modules.safety.feishu.event_client import restart_ws

    result = await restart_ws()
    return success_response(data=result)


@scheduled_tasks_router.get("/feishu/ws/status", response_model=ApiResponse, summary="查询飞书 WebSocket 连接状态")
async def get_feishu_ws_status(current_user: RequiredUser) -> Any:
    """查询安全模块飞书 WebSocket 当前状态。

    返回是否已连接、已注册事件类型、最大重试次数。
    """
    from app.modules.safety.feishu.event_client import get_ws_status

    result = await get_ws_status()
    return success_response(data=result)
