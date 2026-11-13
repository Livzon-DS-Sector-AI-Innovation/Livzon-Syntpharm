"""偏差模块组织配置 API：部门联系人 / 通知设置 / 部门周确认。

路由与台账 router 同级无冲突：台账占 ``/quality/deviation/ledger/*``，
本 router 占 ``/quality/department-contacts`` 与 ``/quality/deviation/notify``、
``/quality/deviation/weekly-confirmations``，均无动态段互相吞并。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import ApiResponse, build_response

from .deviation_config_schemas import (
    ConfigDeleteResultApiResponse,
    ConfigDeleteResultData,
    DepartmentContactApiResponse,
    DepartmentContactCreateRequest,
    DepartmentContactListApiResponse,
    DepartmentContactListData,
    DepartmentContactUpdateRequest,
    MemberOptionListApiResponse,
    MemberOptionListData,
    NotifySettingsApiResponse,
    NotifySettingsUpdateRequest,
    NotifyTestResultApiResponse,
    WeeklyConfirmationApiResponse,
    WeeklyConfirmationListApiResponse,
    WeeklyConfirmationUpsertRequest,
)
from .deviation_config_service import DeviationConfigService

router = APIRouter(tags=["质量管理 - 偏差配置"])

_READ = "quality:deviation:read"
_UPDATE = "quality:deviation:update"


def _actor_id(ctx: PermissionContext, current_user: object) -> UUID | None:
    """操作人 ID：优先取当前登录用户，其次取权限上下文里的 user。"""
    user_id = getattr(current_user, "id", None)
    if isinstance(user_id, UUID):
        return user_id
    ctx_user = getattr(ctx, "user", None)
    ctx_id = getattr(ctx_user, "id", None)
    return ctx_id if isinstance(ctx_id, UUID) else None


# ── 部门联系人 ────────────────────────────────────────────────────────


@router.get(
    "/department-contacts",
    response_model=DepartmentContactListApiResponse,
    summary="部门联系人列表",
)
async def list_department_contacts(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
    keyword: str | None = Query(None, description="部门名称关键字"),
) -> ApiResponse:
    """列出全部部门联系人（含部门负责人 / QA / 质量负责人姓名）。"""
    items = await DeviationConfigService(db).list_contacts(keyword=keyword)
    return build_response(data=DepartmentContactListData(items=items, total=len(items)))


@router.get(
    "/department-contacts/member-options",
    response_model=MemberOptionListApiResponse,
    summary="人员候选",
)
async def list_member_options(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
    keyword: str | None = Query(None, description="姓名或部门关键字"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
) -> ApiResponse:
    """配置页下拉的人员候选。"""
    items = await DeviationConfigService(db).member_options(keyword=keyword, limit=limit)
    return build_response(data=MemberOptionListData(items=items))


@router.post(
    "/department-contacts",
    response_model=DepartmentContactApiResponse,
    summary="新增部门联系人",
)
async def create_department_contact(
    payload: DepartmentContactCreateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """新增部门联系人；同名配置已存在时提示改为编辑。"""
    item = await DeviationConfigService(db).create_contact(payload, actor_id=_actor_id(ctx, current_user))
    return build_response(message="添加成功", data=item)


@router.put(
    "/department-contacts/{contact_id}",
    response_model=DepartmentContactApiResponse,
    summary="编辑部门联系人",
)
async def update_department_contact(
    contact_id: UUID,
    payload: DepartmentContactUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """编辑部门联系人（部门名称为唯一键，不在本接口修改）。"""
    item = await DeviationConfigService(db).update_contact(contact_id, payload, actor_id=_actor_id(ctx, current_user))
    return build_response(message="更新成功", data=item)


@router.delete(
    "/department-contacts/{contact_id}",
    response_model=ConfigDeleteResultApiResponse,
    summary="删除部门联系人",
)
async def delete_department_contact(
    contact_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """软删除部门联系人。"""
    deleted_id = await DeviationConfigService(db).delete_contact(contact_id, actor_id=_actor_id(ctx, current_user))
    return build_response(message="删除成功", data=ConfigDeleteResultData(id=deleted_id, deleted=True))


# ── 通知设置 ──────────────────────────────────────────────────────────


@router.get("/deviation/notify", response_model=NotifySettingsApiResponse, summary="偏差通知设置")
async def get_notify_settings(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """读取群聊接收方与各类通知开关。"""
    return build_response(data=await DeviationConfigService(db).get_notify_settings())


@router.put("/deviation/notify", response_model=NotifySettingsApiResponse, summary="更新偏差通知设置")
async def update_notify_settings(
    payload: NotifySettingsUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """写入群聊接收方与各类通知开关（下次通知即时生效）。"""
    settings = await DeviationConfigService(db).update_notify_settings(payload, actor_id=_actor_id(ctx, current_user))
    return build_response(message="更新成功", data=settings)


@router.post(
    "/deviation/notify/test",
    response_model=NotifyTestResultApiResponse,
    summary="发送偏差通知测试消息",
)
async def send_notify_test(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """给当前登录人发一张测试卡片，并返回飞书凭证 / 各处理人绑定情况的自检结果。"""
    data = await DeviationConfigService(db).send_notify_test(
        actor_id=_actor_id(ctx, current_user),
        actor_name=getattr(current_user, "name", "") or "",
    )
    return build_response(message=data.message, data=data)


# ── 部门周确认 ────────────────────────────────────────────────────────


@router.get(
    "/deviation/weekly-confirmations",
    response_model=WeeklyConfirmationListApiResponse,
    summary="部门周确认列表",
)
async def list_weekly_confirmations(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
    week_key: str | None = Query(None, description="周标识，如 2026-W46；留空取当前周"),
) -> ApiResponse:
    """按周列出所有部门的确认情况（未确认的部门也会返回）。"""
    data = await DeviationConfigService(db).list_weekly_confirmations(week_key)
    return build_response(data=data)


@router.post(
    "/deviation/weekly-confirmations",
    response_model=WeeklyConfirmationApiResponse,
    summary="提交部门周确认",
)
async def upsert_weekly_confirmation(
    payload: WeeklyConfirmationUpsertRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """提交 / 覆盖本部门本周的生产状态与偏差提交状态。"""
    item = await DeviationConfigService(db).upsert_weekly_confirmation(payload, actor_id=_actor_id(ctx, current_user))
    return build_response(message="确认成功", data=item)
