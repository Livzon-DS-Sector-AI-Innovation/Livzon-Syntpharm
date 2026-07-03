import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.response import success_response
from app.platform.identity.deps import AdminUser, CurrentUser
from app.platform.identity.repository import DepartmentRepository, UserRepository
from app.platform.identity.schemas import (
    DepartmentResponse,
    DepartmentTreeNode,
    FeishuCardCallbackResponse,
    FeishuConfigApiResponse,
    FeishuConfigUpsert,
    FeishuDiagnosticApiResponse,
    LocalLoginRequest,
    LocalUserCreate,
    PasswordResetRequest,
    PersonnelItem,
    PersonnelListResponse,
    TokenResponse,
    UserManagementItem,
    UserManagementListResponse,
    UserManagementUpdate,
    UserResponse,
)

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["认证"])
user_router = APIRouter(tags=["用户信息"])
dept_router = APIRouter(prefix="/departments", tags=["组织架构"])
personnel_router = APIRouter(prefix="/personnel", tags=["人员名单"])
sync_router = APIRouter(prefix="/sync", tags=["飞书同步"])
feishu_config_router = APIRouter(prefix="/feishu-config", tags=["Livzon 助手飞书设置"])
feishu_router = APIRouter(prefix="/feishu", tags=["Livzon 助手飞书"])


# ── Auth (SSO) ──────────────────────────────────────────────────────


@auth_router.get("/login", summary="兼容登录入口（默认进入工作台）")
async def login(
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Compatibility entrypoint: login is disabled, so enter the workspace."""
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/production",
        status_code=302,
    )


@auth_router.post(
    "/local/login", summary="本地账号登录", response_model=TokenResponse
)
async def local_login(
    payload: LocalLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Login with local username/password and return the same JWT used by SSO."""
    from app.platform.identity.service import authenticate_local_user

    user, token = await authenticate_local_user(
        db, username=payload.username, password=payload.password
    )
    response = TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
    return success_response(data=response.model_dump(mode="json"))


@auth_router.get("/callback", summary="飞书 SSO 回调")
async def auth_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Handle the OAuth callback from Feishu.

    Exchanges code for tokens, upserts user, generates JWT, then redirects
    to the frontend with the token as a query parameter.
    """
    from app.platform.identity.service import (
        handle_oauth_callback,
        validate_state_token,
    )

    # Validate state for CSRF protection
    if state and not validate_state_token(state):
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=invalid_state",
            status_code=302,
        )

    try:
        user, token = await handle_oauth_callback(db, code)
    except Exception:
        logger.exception("OAuth callback failed")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=callback_failed",
            status_code=302,
        )

    # Redirect to frontend with token
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?token={token}",
        status_code=302,
    )


@auth_router.get("/logout", summary="兼容登出入口（默认返回工作台）")
async def logout(
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Compatibility entrypoint: logout clears client state and returns home."""
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/production",
        status_code=302,
    )


# ── Current User ────────────────────────────────────────────────────


@user_router.get("/me", summary="获取当前平台用户信息")
async def get_me(
    current_user: CurrentUser,
) -> JSONResponse:
    """Return the current platform user, defaulting to the system administrator."""
    assert current_user is not None
    return success_response(data=UserResponse.model_validate(current_user).model_dump())


# ── User Management ────────────────────────────────────────────────


@user_router.get(
    "/users", summary="管理员查询用户列表", response_model=UserManagementListResponse
)
async def list_users(
    keyword: str | None = Query(None, description="按姓名/账号/邮箱/手机号/工号搜索"),
    role: str | None = Query(None, pattern="^(admin|user)$"),
    status_filter: str | None = Query(
        None, alias="status", pattern="^(active|disabled)$"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = None,
) -> JSONResponse:
    repo = UserRepository()
    users, total = await repo.list_users(
        db,
        keyword=keyword,
        role=role,
        status=status_filter,
        offset=offset,
        limit=limit,
    )
    response = UserManagementListResponse(
        items=[UserManagementItem.model_validate(user) for user in users],
        total=total,
        offset=offset,
        limit=limit,
    )
    return success_response(data=response.model_dump(mode="json"))


@user_router.post(
    "/users", summary="管理员创建本地用户", response_model=UserManagementItem
)
async def create_local_user(
    payload: LocalUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = None,
) -> JSONResponse:
    from app.platform.identity.service import hash_password

    repo = UserRepository()
    existing = await repo.get_by_username(db, payload.username)
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在")

    user = await repo.create(
        db,
        username=payload.username,
        password_hash=hash_password(payload.password),
        name=payload.name,
        email=payload.email,
        mobile=payload.mobile,
        employee_no=payload.employee_no,
        department=payload.department,
        position=payload.position,
        role=payload.role,
        status=payload.status,
        auth_source="local",
    )
    user.created_by = current_user.id
    user.updated_by = current_user.id
    await db.flush()
    return success_response(
        data=UserManagementItem.model_validate(user).model_dump(mode="json")
    )


@user_router.put(
    "/users/{user_id}", summary="管理员更新用户", response_model=UserManagementItem
)
async def update_user(
    user_id: UUID,
    payload: UserManagementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = None,
) -> JSONResponse:
    repo = UserRepository()
    user = await repo.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    user.updated_by = current_user.id
    await db.flush()
    return success_response(
        data=UserManagementItem.model_validate(user).model_dump(mode="json")
    )


@user_router.post("/users/{user_id}/reset-password", summary="管理员重置用户密码")
async def reset_user_password(
    user_id: UUID,
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = None,
) -> JSONResponse:
    from app.platform.identity.service import hash_password

    repo = UserRepository()
    user = await repo.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    user.password_hash = hash_password(payload.password)
    user.auth_source = user.auth_source or "local"
    user.updated_by = current_user.id
    await db.flush()
    return success_response(data={"message": "密码已重置"})


# ── Departments ─────────────────────────────────────────────────────


def _build_department_tree(
    depts: list, parent_id: str | None = None,
) -> list[DepartmentTreeNode]:
    """递归构建部门树。"""
    result: list[DepartmentTreeNode] = []
    for d in depts:
        if d.parent_feishu_department_id == parent_id or (
            parent_id is None and not d.parent_feishu_department_id
        ):
            node = DepartmentTreeNode(
                id=d.id,
                feishu_department_id=d.feishu_department_id,
                name=d.name,
                member_count=d.member_count,
                leader_user_id=d.leader_user_id,
                order=d.order,
                children=_build_department_tree(
                    depts, d.feishu_department_id,
                ),
            )
            result.append(node)
    return result


@dept_router.get("", summary="获取部门列表 / 组织架构树")
async def list_departments(
    tree: bool = Query(False, description="是否返回树形结构"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取所有部门。传 ?tree=true 返回层级组织架构树。"""
    repo = DepartmentRepository()
    depts = await repo.list_all(db)

    if tree:
        nodes = _build_department_tree(depts, parent_id=None)
        return success_response(data=[n.model_dump() for n in nodes])

    return success_response(
        data=[DepartmentResponse.model_validate(d).model_dump() for d in depts],
    )


@dept_router.get("/{dept_id}", summary="获取部门详情")
async def get_department(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """按 open_department_id 获取单个部门详情。"""
    repo = DepartmentRepository()
    dept = await repo.get_by_feishu_id(db, dept_id)
    if dept is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="部门不存在")
    return success_response(data=DepartmentResponse.model_validate(dept).model_dump())


# ── Personnel ───────────────────────────────────────────────────────


@personnel_router.get("", summary="获取人员名单")
async def list_personnel(
    department_id: str | None = Query(None, description="按部门 ID 筛选"),
    keyword: str | None = Query(None, description="按姓名搜索"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """分页获取所有人员名单，支持按部门和姓名筛选。"""
    repo = UserRepository()
    users, total = await repo.list_all(
        db,
        department_id=department_id,
        keyword=keyword,
        offset=offset,
        limit=limit,
    )

    items = [PersonnelItem.model_validate(u).model_dump() for u in users]
    resp = PersonnelListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
    return success_response(data=resp.model_dump())


# ── Sync ────────────────────────────────────────────────────────────


@feishu_config_router.get(
    "",
    summary="获取 Livzon 助手飞书设置",
    response_model=FeishuConfigApiResponse,
)
async def get_livzon_feishu_config(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = None,
) -> JSONResponse:
    """获取仅用于 Livzon 助手的飞书通讯录配置。"""
    from app.platform.identity.service import get_livzon_feishu_config_response

    data = await get_livzon_feishu_config_response(db)
    return success_response(data=data.model_dump(mode="json"))


@feishu_config_router.put(
    "",
    summary="保存 Livzon 助手飞书设置",
    response_model=FeishuConfigApiResponse,
)
async def save_livzon_feishu_config(
    payload: FeishuConfigUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = None,
) -> JSONResponse:
    """保存仅用于 Livzon 助手的飞书自建应用凭证。"""
    from app.platform.identity.service import (
        save_livzon_feishu_config as save_config,
    )

    data = await save_config(db, payload)
    return success_response(data=data.model_dump(mode="json"))


@feishu_config_router.post(
    "/test",
    summary="诊断 Livzon 助手飞书权限",
    response_model=FeishuDiagnosticApiResponse,
)
async def test_livzon_feishu_config(
    payload: FeishuConfigUpsert | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = None,
) -> JSONResponse:
    """通过实际飞书 API 调用诊断 Livzon 助手通讯录权限。"""
    from app.platform.identity.service import diagnose_livzon_feishu_config

    data = await diagnose_livzon_feishu_config(db, payload)
    return success_response(data=data.model_dump(mode="json"))


@feishu_router.post(
    "/card-callback",
    summary="Livzon 助手飞书交互卡片回调",
    response_model=FeishuCardCallbackResponse,
)
async def livzon_feishu_card_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """处理 Livzon 助手飞书交互卡片回传事件。"""
    from app.platform.identity.service import handle_livzon_feishu_card_callback

    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无效的飞书回调 JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无效的飞书回调 JSON")
    return await handle_livzon_feishu_card_callback(
        db,
        payload=payload,
        raw_body=raw_body,
        timestamp=request.headers.get("X-Lark-Request-Timestamp"),
        nonce=request.headers.get("X-Lark-Request-Nonce"),
        signature=request.headers.get("X-Lark-Signature"),
    )


@feishu_router.get(
    "/card-callback-ws/status",
    summary="查询 Livzon 助手飞书卡片长连接状态",
)
async def livzon_feishu_card_callback_ws_status(
    current_user: AdminUser = None,
) -> JSONResponse:
    """查询 Livzon 助手飞书卡片回调长连接状态。"""
    from app.platform.identity.feishu_card_ws import get_livzon_card_ws_status

    data = await get_livzon_card_ws_status()
    return success_response(data=data)


@feishu_router.post(
    "/card-callback-ws/restart",
    summary="重启 Livzon 助手飞书卡片长连接",
)
async def restart_livzon_feishu_card_callback_ws(
    current_user: AdminUser = None,
) -> JSONResponse:
    """重启 Livzon 助手飞书卡片回调长连接。"""
    from app.platform.identity.feishu_card_ws import restart_livzon_card_ws

    data = await restart_livzon_card_ws()
    return success_response(data=data)


@sync_router.post("/departments", summary="触发飞书组织架构同步（异步）")
async def trigger_sync_departments(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """POST 触发一次飞书组织架构同步，后台执行不阻塞，立即返回。"""
    from app.core.secrets import decrypt_secret
    from app.platform.identity.repository import FeishuConfigRepository

    config = await FeishuConfigRepository().get_active(db)
    root_id = (
        config.sync_root_department_id
        if config and config.sync_root_department_id
        else settings.FEISHU_SYNC_ROOT_DEPT_ID
    )
    if not root_id:
        return JSONResponse(status_code=400, content={"message": "未配置同步根部门 ID"})

    from app.platform.integrations.feishu.sync import sync_departments

    app_id = config.app_id if config else None
    app_secret = decrypt_secret(config.encrypted_app_secret) if config else None
    asyncio.create_task(sync_departments(root_id, app_id=app_id, app_secret=app_secret))
    logger.info("Department sync triggered for root=%s", root_id)
    return success_response(
        data={"message": "组织架构同步已触发", "root_dept_id": root_id},
    )


@sync_router.post("/members", summary="触发飞书成员同步（异步）")
async def trigger_sync_members(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """POST 触发一次飞书成员同步，后台执行不阻塞，立即返回。"""
    from app.core.secrets import decrypt_secret
    from app.platform.identity.repository import FeishuConfigRepository

    config = await FeishuConfigRepository().get_active(db)
    target_id = (
        config.sync_member_department_id
        if config and config.sync_member_department_id
        else settings.FEISHU_SYNC_MEMBER_DEPT_ID
    )
    if not target_id:
        return JSONResponse(
            status_code=400,
            content={"message": "未配置成员同步部门 ID"},
        )

    from app.platform.integrations.feishu.sync import sync_members

    app_id = config.app_id if config else None
    app_secret = decrypt_secret(config.encrypted_app_secret) if config else None
    asyncio.create_task(sync_members(target_id, app_id=app_id, app_secret=app_secret))
    logger.info("Member sync triggered for target=%s", target_id)
    return success_response(
        data={"message": "成员同步已触发", "target_dept_id": target_id},
    )


@sync_router.post("/all", summary="同步 Livzon 助手飞书通讯录")
async def trigger_sync_all(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = None,
) -> JSONResponse:
    """同步 Livzon 助手使用的部门、用户、手机号、邮箱和部门关系。"""
    from app.platform.identity.service import run_livzon_feishu_sync_all

    data = await run_livzon_feishu_sync_all(db)
    return success_response(data=data)
