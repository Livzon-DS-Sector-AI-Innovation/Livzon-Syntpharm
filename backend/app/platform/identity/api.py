import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.jobs import spawn_task
from app.core.response import success_response
from app.platform.identity.deps import CurrentUser
from app.platform.identity.repository import DepartmentRepository, UserRepository
from app.platform.identity.schemas import (
    DepartmentResponse,
    DepartmentTreeNode,
    PersonnelItem,
    PersonnelListResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["认证"])
user_router = APIRouter(tags=["用户信息"])
dept_router = APIRouter(prefix="/departments", tags=["组织架构"])
personnel_router = APIRouter(prefix="/personnel", tags=["人员名单"])
sync_router = APIRouter(prefix="/sync", tags=["飞书同步"])


# ── Auth (SSO) ──────────────────────────────────────────────────────


@auth_router.post("/test-login", summary="E2E 测试登录（仅开发/测试环境）")
async def test_login(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_e2e_secret: str | None = Header(None, alias="X-E2E-Secret"),
) -> dict[str, Any]:
    """Return a JWT for the e2e test user. Requires APP_ENV=development/test + X-E2E-Secret header."""
    if settings.APP_ENV not in ("development", "test", "e2e"):
        raise HTTPException(status_code=404)

    expected_secret = settings.E2E_AUTH_SECRET
    if x_e2e_secret != expected_secret:
        raise HTTPException(status_code=404)

    from app.platform.identity.service import generate_jwt, get_or_create_e2e_user

    user = await get_or_create_e2e_user(db)
    await db.commit()
    token = generate_jwt(user)
    return {"token": token, "user": {"id": str(user.id), "name": user.name}}


@auth_router.get("/login", summary="发起飞书 SSO 登录")
async def login(
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
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
    settings: Settings = Depends(get_settings),
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

    ip_address = request.client.host if request.client else None
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
            url=f"{settings.FRONTEND_URL}/login?error=invalid_state",
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
            url=f"{settings.FRONTEND_URL}/login?error=callback_failed",
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

    # Redirect to frontend with token
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?token={token}",
        status_code=302,
    )


@auth_router.get("/logout", summary="登出")
async def logout(
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Redirect to frontend login page (frontend handles cookie clearing)."""
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/login",
        status_code=302,
    )


# ── Current User ────────────────────────────────────────────────────


@user_router.get("/me", summary="获取当前登录用户信息")
async def get_me(
    current_user: CurrentUser,
) -> JSONResponse:
    """Return the currently authenticated user's profile.

    Authentication via Bearer header or auth_token cookie.
    """
    if current_user is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="未登录或登录已过期")
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


@sync_router.post("/departments", summary="触发飞书组织架构同步（异步）")
async def trigger_sync_departments(
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """POST 触发一次飞书组织架构同步，后台执行不阻塞，立即返回。"""
    root_id = settings.feishu.platform.sync_root_dept_id
    if not root_id:
        return JSONResponse(
            status_code=400,
            content={"message": "未配置 FEISHU_SYNC_ROOT_DEPT_ID"},
        )

    from app.platform.integrations.feishu.sync import sync_departments

    spawn_task(sync_departments(root_id), name="identity.sync_departments")  # type: ignore[arg-type]
    logger.info("Department sync triggered for root=%s", root_id)
    return success_response(
        data={"message": "组织架构同步已触发", "root_dept_id": root_id},
    )


@sync_router.post("/members", summary="触发飞书成员同步（异步）")
async def trigger_sync_members(
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """POST 触发一次飞书成员同步，后台执行不阻塞，立即返回。"""
    target_id = settings.feishu.platform.sync_member_dept_id
    if not target_id:
        return JSONResponse(
            status_code=400,
            content={"message": "未配置 FEISHU_SYNC_MEMBER_DEPT_ID"},
        )

    from app.platform.integrations.feishu.sync import sync_members

    spawn_task(sync_members(target_id), name="identity.sync_members")  # type: ignore[arg-type]
    logger.info("Member sync triggered for target=%s", target_id)
    return success_response(
        data={"message": "成员同步已触发", "target_dept_id": target_id},
    )


# ── Login Logs ─────────────────────────────────────────────────────

login_log_router = APIRouter(prefix="/login-logs", tags=["登录记录"])


@login_log_router.get("", summary="查询登录记录")
async def list_login_logs(
    status: str | None = Query(None, description="筛选状态：success / failed"),
    keyword: str | None = Query(None, description="按用户名搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
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
