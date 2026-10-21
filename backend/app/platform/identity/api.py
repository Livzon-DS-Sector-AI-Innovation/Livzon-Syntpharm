import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.jobs import spawn_task
from app.core.response import build_response, success_response
from app.platform.audit.service import record_audit_log
from app.platform.identity.models import User
from app.platform.identity.repository import DepartmentRepository, UserRepository
from app.platform.identity.schemas import (
    ChangePasswordApiResponse,
    ChangePasswordData,
    ChangePasswordRequest,
    DepartmentResponse,
    DepartmentTreeNode,
    FeishuBindRequest,
    FeishuConfigApiResponse,
    FeishuConfigUpsert,
    FeishuDiagnosticApiResponse,
    LocalLoginApiResponse,
    LocalLoginRequest,
    LocalUserCreate,
    PasswordResetApiResponse,
    PasswordResetData,
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


def _client_ip(request: Request) -> str | None:
    """取真实客户端 IP。

    浏览器请求先到 Next.js（`src/proxy.ts` 转发 `/api/v1/*`），所以后端的
    `request.client.host` 是前端容器的地址。这里优先取代理透传的
    X-Forwarded-For 第一跳（最靠近用户的地址），否则退回 X-Real-IP / 直连地址。
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:64]
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()[:64]
    return request.client.host if request.client else None


# ── Auth (SSO) ──────────────────────────────────────────────────────


@auth_router.post("/test-login", summary="E2E 测试登录（仅开发/测试环境）")
async def test_login(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_e2e_secret: str | None = Header(None, alias="X-E2E-Secret"),
) -> dict[str, Any]:
    """Return a JWT for the e2e test user. Requires APP_ENV=test/e2e + X-E2E-Secret header."""
    if settings.APP_ENV not in ("test", "e2e"):
        raise HTTPException(status_code=404)

    if not settings.E2E_AUTH_SECRET:
        raise HTTPException(status_code=404)

    expected_secret = settings.E2E_AUTH_SECRET
    if x_e2e_secret != expected_secret:
        raise HTTPException(status_code=404)

    from app.platform.identity.service import generate_jwt, get_or_create_e2e_user
    from app.platform.permission.public_api import ensure_superadmin

    user = await get_or_create_e2e_user(db)
    # E2E 用例覆盖全部业务模块，逐个授权既脆弱又难维护：直接给测试账号挂超管（幂等）。
    # 只有 APP_ENV=test/e2e 且携带正确 X-E2E-Secret 才能走到这里。
    if user.username:
        await ensure_superadmin(db, user.username)
    await db.commit()
    token = generate_jwt(user)
    return {"token": token, "user": {"id": str(user.id), "name": user.name}}


@auth_router.post("/local/login", summary="本地账号密码登录", response_model=LocalLoginApiResponse)
async def local_login(
    payload: LocalLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LocalLoginApiResponse:
    """本地账号密码登录，成功返回 JWT（与飞书登录共用同一套 token）。

    统一错误消息「账号或密码错误」，避免账号枚举。
    """
    from datetime import timedelta

    from app.core.exceptions import UnauthorizedException
    from app.platform.identity.repository import LoginLogRepository
    from app.platform.identity.service import (
        LOCKOUT_SECONDS,
        MAX_LOGIN_FAILURES,
        generate_jwt,
        verify_password,
    )

    repo = UserRepository()
    log_repo = LoginLogRepository()
    ip_address = _client_ip(request)
    user_agent = request.headers.get("user-agent")

    user = await repo.get_by_login_identifier(db, payload.username)

    # 账号不存在 / 已禁用 / 无密码（如飞书账号）→ 统一拒绝
    if user is None or user.status == "disabled" or not user.password_hash:
        await log_repo.create(
            db,
            status="failed",
            login_type="local",
            # 记下尝试登录的账号：页面「按用户名搜索」才能搜到失败的登录尝试
            user_name=payload.username[:100],
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=f"账号不存在或不可用: {payload.username[:64]}",
        )
        await db.commit()
        raise UnauthorizedException("账号或密码错误")

    # 账号已锁定 → 直接拒绝（锁定期间不计数、不再验证密码）
    if user.locked_until is not None and user.locked_until > datetime.now(UTC):
        raise UnauthorizedException("登录失败次数过多，账号已临时锁定，请稍后再试")

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_LOGIN_FAILURES:
            user.locked_until = datetime.now(UTC) + timedelta(seconds=LOCKOUT_SECONDS)
            user.failed_login_attempts = 0
        await log_repo.create(
            db,
            user_id=user.id,
            user_name=user.name,
            status="failed",
            login_type="local",
            ip_address=ip_address,
            user_agent=user_agent,
            error_message="密码错误",
        )
        await db.commit()
        raise UnauthorizedException("账号或密码错误")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    token = generate_jwt(user)
    await _record_login_session(token, user, ip_address, user_agent)
    await log_repo.create(
        db,
        user_id=user.id,
        user_name=user.name,
        status="success",
        login_type="local",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.commit()

    return LocalLoginApiResponse(
        data=TokenResponse(access_token=token, user=UserResponse.model_validate(user)),
    )


@auth_router.get("/login", summary="发起飞书 SSO 登录")
async def login() -> RedirectResponse:
    """Generate state token and redirect user to Feishu authorization page."""
    from app.platform.identity.service import generate_state_token
    from app.platform.integrations.feishu.oauth import FeishuOAuthClient

    state = generate_state_token()
    oauth = FeishuOAuthClient.from_settings()
    authorize_url = oauth.build_authorize_url(state)
    return RedirectResponse(url=authorize_url, status_code=302)


@auth_router.get("/callback", summary="飞书 SSO 回调")
async def auth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle the OAuth callback from Feishu.

    Exchanges code for tokens, upserts user, generates JWT, then redirects
    to the frontend with the token as a query parameter.
    """
    from app.platform.identity.repository import LoginLogRepository
    from app.platform.identity.service import (
        handle_oauth_callback,
        validate_state_token,
    )

    ip_address = _client_ip(request)
    user_agent = request.headers.get("user-agent")
    log_repo = LoginLogRepository()

    # Validate state for CSRF protection
    if state and not validate_state_token(state):
        await log_repo.create(
            db,
            status="failed",
            login_type="feishu_sso",
            ip_address=ip_address,
            user_agent=user_agent,
            error_message="invalid_state: 登录状态已过期",
        )
        await db.commit()
        return RedirectResponse(
            url="/login?error=invalid_state",
            status_code=302,
        )

    try:
        user, token = await handle_oauth_callback(db, code)
    except Exception as exc:
        logger.exception("OAuth callback failed")
        # Rollback any pending transaction before logging the failure
        await db.rollback()
        try:
            await log_repo.create(
                db,
                status="failed",
                login_type="feishu_sso",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=f"OAuth回调失败: {exc}",
            )
            await db.commit()
        except Exception as log_exc:
            logger.error("Failed to record login failure: %s", log_exc)
        return RedirectResponse(
            url="/login?error=callback_failed",
            status_code=302,
        )

    # Record successful login
    await log_repo.create(
        db,
        user_id=user.id,
        user_name=user.name,
        status="success",
        login_type="feishu_sso",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.commit()

    # 会话登记（踢下线用）
    await _record_login_session(token, user, ip_address, user_agent)

    # Redirect to frontend with token
    return RedirectResponse(
        url=f"/auth/callback?token={token}",
        status_code=302,
    )


@auth_router.get("/logout", summary="登出")
async def logout() -> RedirectResponse:
    """Redirect to frontend login page (frontend handles cookie clearing)."""
    return RedirectResponse(
        url="/login",
        status_code=302,
    )


# ── Current User ────────────────────────────────────────────────────


@user_router.get("/me", summary="获取当前登录用户信息")
async def get_me(
    current_user: RequiredUser,
) -> JSONResponse:
    """Return the currently authenticated user's profile.

    Authentication via Bearer header or auth_token cookie.
    """
    return success_response(data=UserResponse.model_validate(current_user).model_dump())


# ── Departments ─────────────────────────────────────────────────────


def _build_department_tree(
    depts: list[Any],
    parent_id: str | None = None,
) -> list[DepartmentTreeNode]:
    """递归构建部门树。"""
    result: list[DepartmentTreeNode] = []
    for d in depts:
        if d.parent_feishu_department_id == parent_id or (parent_id is None and not d.parent_feishu_department_id):
            node = DepartmentTreeNode(
                id=d.id,
                feishu_department_id=d.feishu_department_id,
                name=d.name,
                member_count=d.member_count,
                leader_user_id=d.leader_user_id,
                order=d.order,
                children=_build_department_tree(
                    depts,
                    d.feishu_department_id,
                ),
            )
            result.append(node)
    return result


@dept_router.get("", summary="获取部门列表 / 组织架构树")
async def list_departments(
    current_user: RequiredUser,
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
    current_user: RequiredUser,
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
    current_user: RequiredUser,
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


@sync_router.post("/departments", summary="触发飞书组织架构同步（异步）")
async def trigger_sync_departments(
    ctx: PermissionContext = Depends(require_permission("platform:config:manage")),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """POST 触发一次飞书组织架构同步，后台执行不阻塞，立即返回。"""
    # root_id 允许为空：为空时由 get_all_departments 自动从「应用可见范围内的部门」出发
    # （应用可见范围通常不含根部门 "0"，硬编码 "0" 会报 40004 no dept authority error）
    root_id = settings.feishu.platform.sync_root_dept_id or None

    from app.platform.integrations.feishu.sync import sync_departments

    spawn_task(sync_departments(root_id), name="identity.sync_departments")
    logger.info("Department sync triggered for root=%s", root_id or "(自动：可见范围内的部门)")
    return success_response(
        data={"message": "组织架构同步已触发", "root_dept_id": root_id or "auto"},
    )


@sync_router.post("/members", summary="触发飞书成员同步（异步）")
async def trigger_sync_members(
    ctx: PermissionContext = Depends(require_permission("platform:config:manage")),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """POST 触发一次飞书成员同步，后台执行不阻塞，立即返回。"""
    # target_id 允许为空：为空时由 sync_members 自动从「应用可见范围内的部门」出发
    target_id = settings.feishu.platform.sync_member_dept_id or None

    from app.platform.integrations.feishu.sync import sync_members

    spawn_task(sync_members(target_id), name="identity.sync_members")
    logger.info("Member sync triggered for target=%s", target_id or "(自动)")
    return success_response(
        data={"message": "成员同步已触发", "target_dept_id": target_id or "auto"},
    )


@sync_router.post("/all", summary="同步 Livzon 助手飞书通讯录（部门 + 成员，后台执行）")
async def trigger_sync_all(
    ctx: PermissionContext = Depends(require_permission("platform:config:manage")),
) -> JSONResponse:
    """POST 触发一次「部门 + 成员」全量同步。

    全量同步耗时较长（数百人约 50 秒），按项目规范走后台任务、不阻塞请求；
    结果写入飞书配置的 last_sync_status / last_sync_message / last_synced_at。
    """
    from app.platform.identity.service import sync_livzon_feishu_contacts_all

    spawn_task(sync_livzon_feishu_contacts_all(), name="identity.sync_all")
    logger.info("Livzon Feishu contacts sync (departments + members) triggered")
    return success_response(
        data={
            "status": "ok",
            "message": "通讯录同步已在后台开始（部门 + 成员），约 1 分钟后刷新本页查看结果。",
        },
    )


# ── Livzon Feishu Config ──────────────────────────────────────────

feishu_config_router = APIRouter(prefix="/feishu-config", tags=["Livzon 飞书配置"])


@feishu_config_router.get("", summary="获取 Livzon 飞书配置", response_model=FeishuConfigApiResponse)
async def get_feishu_config(
    ctx: PermissionContext = Depends(require_permission("platform:config:read")),
    db: AsyncSession = Depends(get_db),
) -> FeishuConfigApiResponse:
    """获取当前 Livzon 飞书配置"""
    from app.platform.identity.service import get_livzon_feishu_config_response

    config = await get_livzon_feishu_config_response(db)
    return FeishuConfigApiResponse(data=config)


@feishu_config_router.put("", summary="保存 Livzon 飞书配置", response_model=FeishuConfigApiResponse)
async def save_feishu_config(
    payload: FeishuConfigUpsert,
    ctx: PermissionContext = Depends(require_permission("platform:config:manage")),
    db: AsyncSession = Depends(get_db),
) -> FeishuConfigApiResponse:
    """保存 Livzon 飞书配置"""
    from app.platform.identity.service import save_livzon_feishu_config

    config = await save_livzon_feishu_config(db, payload)
    await db.commit()
    return FeishuConfigApiResponse(data=config)


@feishu_config_router.post("/test", summary="测试 Livzon 飞书配置", response_model=FeishuDiagnosticApiResponse)
async def test_feishu_config(
    ctx: PermissionContext = Depends(require_permission("platform:config:manage")),
    payload: FeishuConfigUpsert | None = None,
    db: AsyncSession = Depends(get_db),
) -> FeishuDiagnosticApiResponse:
    """测试 Livzon 飞书配置连接"""
    from app.platform.identity.service import diagnose_livzon_feishu_config

    result = await diagnose_livzon_feishu_config(db, payload)
    return FeishuDiagnosticApiResponse(data=result)


# ── Login Logs ─────────────────────────────────────────────────────

login_log_router = APIRouter(prefix="/login-logs", tags=["登录记录"])


@login_log_router.get("", summary="查询登录记录")
async def list_login_logs(
    ctx: PermissionContext = Depends(require_permission("platform:audit:read")),
    status: str | None = Query(None, description="筛选状态：success / failed"),
    keyword: str | None = Query(None, description="按用户名搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """分页查询登录记录，支持按状态和用户名筛选。"""
    from app.platform.identity.repository import LoginLogRepository
    from app.platform.identity.schemas import LoginLogListResponse, LoginLogResponse

    repo = LoginLogRepository()
    logs, total = await repo.list_logs(
        db,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    items = [LoginLogResponse.model_validate(log).model_dump() for log in logs]
    resp = LoginLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
    return success_response(data=resp.model_dump())


# ── 用户管理（管理页）──────────────────────────────────────────────


@user_router.get("/users", summary="用户管理列表")
async def list_users_management(
    ctx: PermissionContext = Depends(require_permission("platform:user:read")),
    keyword: str | None = Query(None, description="按姓名/账号/邮箱/手机号搜索"),
    status: str | None = Query(None, description="按状态筛选"),
    auth_source: str | None = Query(None, description="按账号来源筛选：local / feishu"),
    unbound_only: bool = Query(False, description="仅返回未绑定飞书身份的账号"),
    must_change_password: bool | None = Query(None, description="按「待改密」筛选"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    repo = UserRepository()
    # 超管账号只对超管可见：非超管即使有 platform:user:read，也不返回超管行
    # （否则会泄露超管姓名、联系方式与所持角色）。
    from app.platform.permission.public_api import list_superuser_user_ids, user_is_superuser

    exclude_user_ids = None
    if not await user_is_superuser(db, ctx.user):
        exclude_user_ids = await list_superuser_user_ids(db)

    users, total = await repo.list_users(
        db,
        keyword=keyword,
        status=status,
        auth_source=auth_source,
        unbound_only=unbound_only,
        must_change_password=must_change_password,
        exclude_user_ids=exclude_user_ids,
        offset=offset,
        limit=limit,
    )
    items = []
    roles_map = await repo.get_roles_for_users(db, [u.id for u in users])
    for u in users:
        item = UserManagementItem.model_validate(u)
        item.roles = roles_map.get(u.id, [])
        items.append(item.model_dump())
    resp = UserManagementListResponse(items=items, total=total, offset=offset, limit=limit)
    return success_response(data=resp.model_dump())


@user_router.post("/users", summary="新建本地用户")
async def create_user_management(
    payload: LocalUserCreate,
    ctx: PermissionContext = Depends(require_permission("platform:user:manage")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    from app.core.exceptions import BadRequestException, DuplicateException
    from app.platform.identity.service import hash_password, validate_password_strength

    repo = UserRepository()
    existing = await repo.get_by_username(db, payload.username)
    if existing is not None:
        raise DuplicateException("用户名", payload.username)

    strength_error = validate_password_strength(payload.password)
    if strength_error:
        raise BadRequestException(strength_error)

    user = await repo.create(
        db,
        name=payload.name,
        username=payload.username,
        password_hash=hash_password(payload.password),
        email=payload.email,
        mobile=payload.mobile,
        employee_no=payload.employee_no,
        department=payload.department,
        position=payload.position,
        status=payload.status,
        auth_source="local",
    )
    await record_audit_log(
        db,
        user=ctx.user,
        action="user.create",
        resource_type="user",
        resource_id=user.id,
        new_value={"username": payload.username, "name": payload.name, "status": payload.status},
    )
    await db.commit()
    return success_response(data=UserManagementItem.model_validate(user).model_dump())


@user_router.put("/users/{user_id}", summary="更新用户")
async def update_user_management(
    user_id: uuid.UUID,
    payload: UserManagementUpdate,
    ctx: PermissionContext = Depends(require_permission("platform:user:manage")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    from app.core.exceptions import ForbiddenException, NotFoundException

    repo = UserRepository()
    user = await repo.get_by_id(db, user_id)
    if user is None:
        raise NotFoundException("用户")

    # 超管保护 + 防越级：非超管不能操作超管账号；下级管理员只能管理权限严格低于自己的账号
    from app.platform.permission.public_api import guard_manage_target

    await guard_manage_target(db, actor=ctx.user, target=user)

    # 防自我提权：不能修改自己的账号状态
    if user.id == ctx.user.id and payload.status is not None and payload.status != user.status:
        raise ForbiddenException("不能修改自己的状态")

    # 已绑定飞书的账号：人员资料以飞书为准（每次登录自动同步，手工改了也会被覆盖），
    # 因此禁止手工修改；状态属于平台侧管理字段，仍允许修改
    # （状态另有表格上的「启用 / 禁用」按钮）。
    if user.feishu_open_id or user.feishu_user_id:
        managed_fields = {
            "name": "姓名",
            "email": "邮箱",
            "mobile": "手机号",
            "employee_no": "工号",
            "department": "部门",
            "position": "职位",
        }
        changed_labels = [
            label
            for field_name, label in managed_fields.items()
            if getattr(payload, field_name) is not None and getattr(payload, field_name) != getattr(user, field_name)
        ]
        if changed_labels:
            raise ForbiddenException(
                f"该账号已绑定飞书，{'、'.join(changed_labels)}由飞书自动同步，不能手工修改",
            )

    # 登录用户名创建后不允许修改：它是登录凭据与审计追溯的锚点，改名会让历史记录难以对应
    if payload.username is not None and payload.username.strip() != (user.username or ""):
        raise ForbiddenException("账号创建后不允许修改，如需更换请新建账号")

    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email
    if payload.mobile is not None:
        user.mobile = payload.mobile
    if payload.employee_no is not None:
        user.employee_no = payload.employee_no
    if payload.department is not None:
        user.department = payload.department
    if payload.position is not None:
        user.position = payload.position
    if payload.status is not None:
        user.status = payload.status

    await record_audit_log(
        db,
        user=ctx.user,
        action="user.update",
        resource_type="user",
        resource_id=user.id,
        old_value={"username": user.username, "name": user.name, "status": user.status},
        new_value={
            "username": user.username,
            "name": payload.name if payload.name is not None else user.name,
            "status": payload.status if payload.status is not None else user.status,
        },
    )
    await db.commit()
    return success_response(data=UserManagementItem.model_validate(user).model_dump())


@user_router.post(
    "/users/{user_id}/reset-password",
    summary="重置用户密码（留空则随机生成，明文只返回一次）",
    response_model=PasswordResetApiResponse,
)
async def reset_user_password(
    user_id: uuid.UUID,
    payload: PasswordResetRequest,
    ctx: PermissionContext = Depends(require_permission("platform:user:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """管理员重置密码。

    - 不传 `password`：随机生成，明文在响应里**只返回一次**（不落库），前端弹窗展示；
    - 传 `password`：按管理员指定值设置，响应不含明文；
    - 两种情况都把账号标记为「首登需改密」；
    - 超级管理员账号不允许被他人重置 —— 其密码只能由本人登录后自助修改。
    """
    from app.core.exceptions import ForbiddenException, NotFoundException
    from app.platform.identity.service import reset_password_by_admin
    from app.platform.permission.public_api import user_is_superuser

    repo = UserRepository()
    user = await repo.get_by_id(db, user_id)
    if user is None:
        raise NotFoundException("用户")

    if await user_is_superuser(db, user):
        raise ForbiddenException("超级管理员的密码只能由本人登录后修改")

    generated = await reset_password_by_admin(
        db,
        user=user,
        password=payload.password,
        operator_id=ctx.user.id,
    )
    # 审计：只记录「谁重置了谁的口令」与方式，**绝不记录密码明文**
    await record_audit_log(
        db,
        user=ctx.user,
        action="user.reset_password",
        resource_type="user",
        resource_id=user.id,
        new_value={"random": generated is not None},
    )
    await db.commit()

    # 通知绑定了飞书的用户（卡片不含明文密码，失败静默降级）
    await _notify_password_reset(user)

    return build_response(
        data=PasswordResetData(
            message=(
                "已生成新密码，请立即复制（只显示这一次）" if generated else "密码已重置，该用户下次登录需修改密码"
            ),
            password=generated or None,
        )
    )


async def _notify_password_reset(user: User) -> None:
    """重置密码后通知用户（仅限绑定了飞书的账号；失败静默降级，不影响重置结果）。

    通知**不含明文密码**：明文只在重置响应的弹窗里展示一次，由管理员转交。
    卡片只告知「密码已重置 + 首次登录需改密」，用户可用飞书一键登录。
    """
    open_id = user.feishu_open_id
    if not open_id:
        return
    try:
        from app.platform.integrations.feishu.notification import send_user_card

        content = (
            "你的平台账号密码已由管理员重置。\n\n"
            "**首次登录后需立即设置新密码。**\n"
            "登录方式：\n- 飞书一键登录\n- 账号密码登录（新密码请向管理员获取）"
        )
        await send_user_card(open_id, "账号密码已重置", content)
    except Exception:
        logger.exception("重置密码后发送飞书通知失败（不影响重置结果）")


async def _record_login_session(token: str, user: User, ip_address: str | None, user_agent: str | None) -> None:
    """登录成功后把 jti 登记到 Redis 会话索引（供「踢下线」用）。失败只记日志。"""
    try:
        import jwt as pyjwt

        from app.platform.identity.session import record_session

        payload = pyjwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
        await record_session(jti=payload["jti"], user=user, ip_address=ip_address, user_agent=user_agent)
    except Exception:
        logger.warning("记录登录会话失败", exc_info=True)


@user_router.get("/sessions", summary="在线会话列表")
async def list_sessions(
    ctx: PermissionContext = Depends(require_permission("platform:user:read")),
) -> Any:
    """列出全部在线会话（账号管理员可看，用于识别并踢掉异常会话）。"""
    from app.platform.identity.session import list_all_sessions

    return build_response(data=await list_all_sessions())


@user_router.delete("/sessions/{jti}", summary="吊销会话（踢下线）")
async def revoke_session_api(
    jti: str,
    ctx: PermissionContext = Depends(require_permission("platform:user:manage")),
) -> Any:
    from app.platform.identity.session import revoke_session

    await revoke_session(jti)
    return build_response(data={"revoked": True})


@user_router.delete("/users/{user_id}/sessions", summary="吊销某用户全部会话")
async def revoke_user_sessions(
    user_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("platform:user:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.core.exceptions import NotFoundException
    from app.platform.identity.session import revoke_all_user_sessions

    user = await UserRepository().get_by_id(db, user_id)
    if user is None:
        raise NotFoundException("用户")
    count = await revoke_all_user_sessions(user.id)
    return build_response(data={"revoked": count})


@user_router.post(
    "/me/password",
    summary="修改当前登录用户的密码（自助改密）",
    response_model=ChangePasswordApiResponse,
)
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """当前登录用户自助改密：校验原密码 → 更新 → 清除强制改密标记。

    只要求「已登录」，不挂权限码（已在 `registry.EXEMPT_ROUTES` 登记豁免绑定兜底）。
    """
    from app.platform.identity.service import change_own_password

    await change_own_password(
        db,
        user=current_user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    await record_audit_log(
        db,
        user=current_user,
        action="user.change_password",
        resource_type="user",
        resource_id=current_user.id,
    )
    await db.commit()
    return build_response(data=ChangePasswordData(message="密码已修改"))


@user_router.post("/users/{user_id}/bind-feishu", summary="绑定飞书用户")
async def bind_user_feishu(
    user_id: uuid.UUID,
    payload: FeishuBindRequest,
    ctx: PermissionContext = Depends(require_permission("platform:user:manage")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """把一条飞书用户记录合并进该账号：迁角色授权 + 迁飞书身份 + 软删原记录。

    ⚠️ 产品要求（2026-10-13）：**管理端界面不再提供「绑定飞书」入口** ——
    管理员只能解绑，不能替用户绑定；绑定由用户本人首次飞书登录时自动完成
    （见 `handle_oauth_callback`）。本接口保留，以便后续「系统自动合并重复账号」
    等场景调用；若需彻底禁止人工调用，可把依赖换成更高权限码或直接下线。
    """
    from app.core.exceptions import BadRequestException, NotFoundException
    from app.platform.identity.service import bind_feishu_user

    repo = UserRepository()
    target = await repo.get_by_id(db, user_id)
    if target is None:
        raise NotFoundException("用户")
    # 超管保护 + 防越级
    from app.platform.permission.public_api import guard_manage_target

    await guard_manage_target(db, actor=ctx.user, target=target)
    if target.feishu_open_id or target.feishu_user_id:
        raise BadRequestException("该账号已绑定飞书身份，请先解绑")
    if payload.source_user_id == user_id:
        raise BadRequestException("不能绑定到账号自身")

    source = await repo.get_by_id(db, payload.source_user_id)
    if source is None:
        raise NotFoundException("飞书用户")
    if not (source.feishu_open_id or source.feishu_user_id):
        raise BadRequestException("所选记录不是飞书用户（缺少飞书标识）")

    result = await bind_feishu_user(db, target=target, source=source, operator_id=ctx.user.id)
    data = UserManagementItem.model_validate(target).model_dump()
    data["bind_result"] = result
    return success_response(data=data)


@user_router.delete("/users/{user_id}/bind-feishu", summary="解绑飞书用户")
async def unbind_user_feishu(
    user_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("platform:user:manage")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """解绑飞书身份。

    - 由飞书首次登录自动创建的账号（`auth_source=feishu`）：解绑即**软删除**该账号，
      因为它没有本地密码，解绑后已无可用登录身份；
    - 本地创建后绑定飞书的账号：只清空飞书字段，账号本体与角色授权保留。
    """
    from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
    from app.platform.identity.service import unbind_feishu_user

    repo = UserRepository()
    user = await repo.get_by_id(db, user_id)
    if user is None:
        raise NotFoundException("用户")
    # 超管保护 + 防越级
    from app.platform.permission.public_api import guard_manage_target

    await guard_manage_target(db, actor=ctx.user, target=user)
    if not (user.feishu_open_id or user.feishu_user_id):
        raise BadRequestException("该账号未绑定飞书身份")
    if user.id == ctx.user.id:
        raise ForbiddenException("不能解绑当前登录账号的飞书身份，请让其他管理员操作")

    delete_account = user.auth_source == "feishu"
    if delete_account:
        from app.platform.permission.public_api import list_superuser_user_ids

        super_ids = await list_superuser_user_ids(db)
        if user.id in super_ids and len(super_ids) <= 1:
            raise ForbiddenException("不能删除最后一个超级管理员账号")

    await unbind_feishu_user(
        db,
        user=user,
        operator_id=ctx.user.id,
        delete_account=delete_account,
    )
    await record_audit_log(
        db,
        user=ctx.user,
        action="user.unbind_feishu",
        resource_type="user",
        resource_id=user.id,
        new_value={"account_deleted": delete_account},
    )
    await db.commit()
    data = UserManagementItem.model_validate(user).model_dump()
    data["account_deleted"] = delete_account
    return success_response(data=data)
