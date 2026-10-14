"""权限管理 API。

挂载前缀：/api/v1/permission（见 api/router.py）。
所有管理接口本身受权限保护（platform:* 权限码）。
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, require_current_user, require_permission
from app.core.exceptions import BadRequestException, DuplicateException, ForbiddenException, NotFoundException
from app.core.response import build_response
from app.platform.identity.models import User
from app.platform.permission.models import (
    GRANT_ACTIVE,
    Role,
    RolePermission,
    UserRoleGrant,
)
from app.platform.permission.repository import (
    ApiBindingRepository,
    GrantRepository,
    PermissionRepository,
    RoleRepository,
)
from app.platform.permission.schemas import (
    ApiBindingListResponse,
    ApiBindingResponse,
    GrantCreate,
    GrantDetailApiResponse,
    GrantListResponse,
    GrantResponse,
    GrantUpdate,
    MessageApiResponse,
    MyPermissionsData,
    MyPermissionsResponse,
    PermissionListResponse,
    PermissionResponse,
    PermissionTreeData,
    PermissionTreeNode,
    PermissionTreeResponse,
    RoleCreate,
    RoleDetailApiResponse,
    RoleDetailResponse,
    RoleListResponse,
    RoleUpdate,
)
from app.platform.permission.service.catalog import build_permission_tree
from app.platform.permission.service.management import (
    get_role,
    guard_last_superadmin,
    guard_self_escalation,
)

router = APIRouter(tags=["权限管理"])


# ── 角色 ──────────────────────────────────────────────────────────


@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    ctx: PermissionContext = Depends(require_permission("platform:role:read")),
    db: AsyncSession = Depends(get_db),
):
    role_repo = RoleRepository()
    roles = await role_repo.list_roles(db)
    data = []
    for role in roles:
        codes = await role_repo.list_role_permission_codes(db, role.id)
        data.append(
            RoleDetailResponse(
                id=role.id,
                code=role.code,
                name=role.name,
                category=role.category,
                module_code=role.module_code,
                description=role.description,
                is_builtin=role.is_builtin,
                is_superuser=role.is_superuser,
                status=role.status,
                permission_codes=codes,
            )
        )
    return build_response(data=data)


@router.post("/roles", response_model=RoleDetailApiResponse)
async def create_role(
    payload: RoleCreate,
    ctx: PermissionContext = Depends(require_permission("platform:role:manage")),
    db: AsyncSession = Depends(get_db),
):
    role_repo = RoleRepository()
    existing = await role_repo.get_role_by_code(db, payload.code)
    if existing is not None:
        raise DuplicateException("角色编码", payload.code)

    if payload.category == "module" and not payload.module_code:
        raise BadRequestException("模块角色必须指定模块编码")

    role = Role(
        code=payload.code,
        name=payload.name,
        category=payload.category,
        module_code=payload.module_code,
        description=payload.description,
        is_builtin=False,
        is_superuser=False,
        status=GRANT_ACTIVE,
    )
    db.add(role)
    await db.flush()
    await role_repo.set_role_permissions(db, role.id, payload.permission_codes)
    await db.commit()

    codes = await role_repo.list_role_permission_codes(db, role.id)
    return build_response(
        data=RoleDetailResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            category=role.category,
            module_code=role.module_code,
            description=role.description,
            is_builtin=role.is_builtin,
            is_superuser=role.is_superuser,
            status=role.status,
            permission_codes=codes,
        )
    )


@router.put("/roles/{role_id}", response_model=RoleDetailApiResponse)
async def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdate,
    ctx: PermissionContext = Depends(require_permission("platform:role:manage")),
    db: AsyncSession = Depends(get_db),
):
    role_repo = RoleRepository()
    role = await role_repo.get_role(db, role_id)
    if role is None:
        raise NotFoundException("角色")

    if role.is_builtin and payload.status is not None:
        raise ForbiddenException("内置角色不可禁用")

    # 防间接提权：不能修改自己所属角色的权限（保守策略）
    if payload.permission_codes is not None:
        grant_repo = GrantRepository()
        my_grants = await grant_repo.list_grants(db, user_id=ctx.user.id)
        if any(g.role_id == role.id for g in my_grants):
            raise ForbiddenException("不能修改自己所属角色的权限")

    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description
    if payload.status is not None:
        role.status = payload.status
    if payload.permission_codes is not None:
        await role_repo.set_role_permissions(db, role.id, payload.permission_codes)

    await db.commit()

    codes = await role_repo.list_role_permission_codes(db, role.id)
    return build_response(
        data=RoleDetailResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            category=role.category,
            module_code=role.module_code,
            description=role.description,
            is_builtin=role.is_builtin,
            is_superuser=role.is_superuser,
            status=role.status,
            permission_codes=codes,
        )
    )


@router.delete("/roles/{role_id}", response_model=MessageApiResponse)
async def delete_role(
    role_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("platform:role:manage")),
    db: AsyncSession = Depends(get_db),
):
    role_repo = RoleRepository()
    role = await role_repo.get_role(db, role_id)
    if role is None:
        raise NotFoundException("角色")
    if role.is_builtin:
        raise ForbiddenException("内置角色不可删除")
    if role.is_superuser:
        raise ForbiddenException("超级管理员角色不可删除")

    await role_repo.soft_delete_role(db, role)
    await db.commit()
    return build_response()


# ── 权限目录 ──────────────────────────────────────────────────────


@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    ctx: PermissionContext = Depends(require_permission("platform:permission:read")),
    db: AsyncSession = Depends(get_db),
):
    repo = PermissionRepository()
    perms = await repo.list_permissions(db)
    return build_response(data=[PermissionResponse.model_validate(p).model_dump() for p in perms])


@router.get("/tree", response_model=PermissionTreeResponse)
async def get_permission_tree(
    ctx: PermissionContext = Depends(require_permission("platform:permission:read")),
):
    """权限目录树（模块 → 资源 → 权限码），供角色管理按模块 / 功能勾选权限。

    纯注册表数据、不查库，因此权限表未迁移时也可正常返回。
    """
    tree, total_permissions = build_permission_tree()
    data = PermissionTreeData(
        tree=[PermissionTreeNode(**node) for node in tree],
        total_permissions=total_permissions,
        total_modules=len(tree),
    )
    return build_response(data=data.model_dump())


# ── 接口绑定登记簿 ────────────────────────────────────────────────


@router.get("/api-bindings", response_model=ApiBindingListResponse)
async def list_api_bindings(
    ctx: PermissionContext = Depends(require_permission("platform:api-binding:read")),
    db: AsyncSession = Depends(get_db),
):
    repo = ApiBindingRepository()
    bindings = await repo.list_bindings(db)
    return build_response(data=[ApiBindingResponse.model_validate(b).model_dump() for b in bindings])


# ── 授权管理 ──────────────────────────────────────────────────────


@router.get("/grants", response_model=GrantListResponse)
async def list_grants(
    user_id: uuid.UUID | None = Query(None),
    ctx: PermissionContext = Depends(require_permission("platform:grant:read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserRoleGrant, Role.code, Role.name, User.name)
        .join(Role, Role.id == UserRoleGrant.role_id)
        .outerjoin(User, User.id == UserRoleGrant.user_id)
        .where(UserRoleGrant.is_deleted == False)  # noqa: E712
        .order_by(UserRoleGrant.created_at.desc())
    )
    if user_id is not None:
        stmt = stmt.where(UserRoleGrant.user_id == user_id)
    rows = (await db.execute(stmt)).all()

    data = [
        GrantResponse(
            id=g.id,
            user_id=g.user_id,
            role_id=g.role_id,
            scope_type=g.scope_type,
            scope_dept_codes=g.scope_dept_codes,
            status=g.status,
            granted_by=g.granted_by,
            version=g.version,
            role_code=role_code,
            role_name=role_name,
            user_name=user_name,
        )
        for g, role_code, role_name, user_name in rows
    ]
    return build_response(data=data)


@router.post("/grants", response_model=GrantDetailApiResponse)
async def create_grant(
    payload: GrantCreate,
    ctx: PermissionContext = Depends(require_permission("platform:grant:manage")),
    db: AsyncSession = Depends(get_db),
):
    if payload.user_id == ctx.user.id:
        raise ForbiddenException("不能给自己授权")

    role = await get_role(db, payload.role_id)
    if role is None:
        raise NotFoundException("角色")

    _validate_scope(payload.scope_type, payload.scope_dept_codes)

    grant_repo = GrantRepository()
    grant = await grant_repo.create_grant(
        db,
        user_id=payload.user_id,
        role_id=payload.role_id,
        scope_type=payload.scope_type,
        scope_dept_codes=payload.scope_dept_codes,
        granted_by=ctx.user.id,
    )
    await db.commit()

    return build_response(
        data=GrantResponse(
            id=grant.id,
            user_id=grant.user_id,
            role_id=grant.role_id,
            scope_type=grant.scope_type,
            scope_dept_codes=grant.scope_dept_codes,
            status=grant.status,
            granted_by=grant.granted_by,
            version=grant.version,
            role_code=role.code,
            role_name=role.name,
        )
    )


@router.put("/grants/{grant_id}", response_model=GrantDetailApiResponse)
async def update_grant(
    grant_id: uuid.UUID,
    payload: GrantUpdate,
    ctx: PermissionContext = Depends(require_permission("platform:grant:manage")),
    db: AsyncSession = Depends(get_db),
):
    grant_repo = GrantRepository()
    grant = await grant_repo.get_grant(db, grant_id)
    if grant is None:
        raise NotFoundException("授权")

    guard_self_escalation(ctx.user.id, grant)

    if payload.scope_type is not None:
        _validate_scope(payload.scope_type, payload.scope_dept_codes)
        grant.scope_type = payload.scope_type
        grant.scope_dept_codes = payload.scope_dept_codes
    if payload.status is not None:
        grant.status = payload.status
        grant.version += 1

    await db.commit()

    role = await get_role(db, grant.role_id)
    return build_response(
        data=GrantResponse(
            id=grant.id,
            user_id=grant.user_id,
            role_id=grant.role_id,
            scope_type=grant.scope_type,
            scope_dept_codes=grant.scope_dept_codes,
            status=grant.status,
            granted_by=grant.granted_by,
            version=grant.version,
            role_code=role.code if role else None,
            role_name=role.name if role else None,
        )
    )


@router.delete("/grants/{grant_id}", response_model=MessageApiResponse)
async def delete_grant(
    grant_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("platform:grant:manage")),
    db: AsyncSession = Depends(get_db),
):
    grant_repo = GrantRepository()
    grant = await grant_repo.get_grant(db, grant_id)
    if grant is None:
        raise NotFoundException("授权")

    guard_self_escalation(ctx.user.id, grant)
    await guard_last_superadmin(db, grant)

    grant.is_deleted = True
    await db.commit()
    return build_response()


# ── 当前用户权限 ──────────────────────────────────────────────────


@router.get("/my-permissions", response_model=MyPermissionsResponse)
async def my_permissions(
    user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    grant_repo = GrantRepository()
    if await grant_repo.is_superuser(db, user):
        perms = await PermissionRepository().list_permissions(db)
        return build_response(data=MyPermissionsData(permissions=[p.code for p in perms], is_superuser=True))

    stmt = (
        select(RolePermission.permission_code)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleGrant, UserRoleGrant.role_id == Role.id)
        .where(
            UserRoleGrant.user_id == user.id,
            UserRoleGrant.status == GRANT_ACTIVE,
            UserRoleGrant.is_deleted == False,  # noqa: E712
            Role.status == GRANT_ACTIVE,
            Role.is_deleted == False,  # noqa: E712
            RolePermission.is_deleted == False,  # noqa: E712
        )
        .distinct()
    )
    codes = list((await db.execute(stmt)).scalars().all())
    return build_response(data=MyPermissionsData(permissions=codes, is_superuser=False))


# ── 工具 ──────────────────────────────────────────────────────────


def _validate_scope(scope_type: str, scope_dept_codes: list[str] | None) -> None:
    if scope_type in ("department", "department_and_children") and not scope_dept_codes:
        raise BadRequestException("指定部门范围时必须提供部门编码列表")
