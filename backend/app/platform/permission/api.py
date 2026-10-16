"""权限管理 API。

挂载前缀：/api/v1/permission（见 api/router.py）。
所有管理接口本身受权限保护（platform:* 权限码）。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, require_current_user, require_permission
from app.core.exceptions import BadRequestException, DuplicateException, ForbiddenException, NotFoundException
from app.core.response import build_response
from app.platform.audit.service import record_audit_log
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
    DepartmentOption,
    DepartmentOptionListResponse,
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
from app.platform.permission.cache import evict_user_permission_cache
from app.platform.permission.service.authorization import is_superuser_with_cache
from app.platform.permission.service.management import (
    assert_actor_can_grant_role,
    assert_actor_can_grant_scope,
    effective_permission_codes,
    get_role,
    guard_last_superadmin,
    guard_manage_target,
    guard_self_escalation,
)

router = APIRouter(tags=["权限管理"])


async def _evict_user_cache(user_id: uuid.UUID) -> None:
    await evict_user_permission_cache(user_id)


async def _evict_cache_for_role(db: AsyncSession, role_id: uuid.UUID) -> None:
    user_ids = await GrantRepository().list_active_user_ids_by_role(db, role_id)
    for user_id in user_ids:
        await evict_user_permission_cache(user_id)


# ── 角色 ──────────────────────────────────────────────────────────


@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    ctx: PermissionContext = Depends(require_permission("platform:role:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
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
) -> Any:
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
    await record_audit_log(
        db,
        user=ctx.user,
        action="role.create",
        resource_type="role",
        resource_id=role.id,
        new_value={"code": role.code, "name": role.name, "permission_codes": payload.permission_codes},
    )
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
) -> Any:
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

    await record_audit_log(
        db,
        user=ctx.user,
        action="role.update",
        resource_type="role",
        resource_id=role.id,
        new_value={
            "name": payload.name,
            "description": payload.description,
            "status": payload.status,
            "permission_codes": payload.permission_codes,
        },
    )
    await db.commit()
    await _evict_cache_for_role(db, role.id)

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
) -> Any:
    role_repo = RoleRepository()
    role = await role_repo.get_role(db, role_id)
    if role is None:
        raise NotFoundException("角色")
    if role.is_builtin:
        raise ForbiddenException("内置角色不可删除")
    if role.is_superuser:
        raise ForbiddenException("超级管理员角色不可删除")

    await role_repo.soft_delete_role(db, role)
    await record_audit_log(
        db,
        user=ctx.user,
        action="role.delete",
        resource_type="role",
        resource_id=role.id,
        old_value={"code": role.code, "name": role.name},
    )
    await db.commit()
    await _evict_cache_for_role(db, role.id)
    return build_response()


# ── 权限目录 ──────────────────────────────────────────────────────


@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    ctx: PermissionContext = Depends(require_permission("platform:permission:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = PermissionRepository()
    perms = await repo.list_permissions(db)
    return build_response(data=[PermissionResponse.model_validate(p).model_dump() for p in perms])


@router.get("/tree", response_model=PermissionTreeResponse)
async def get_permission_tree(
    ctx: PermissionContext = Depends(require_permission("platform:role:read")),
) -> Any:
    """权限目录树（模块 → 资源 → 权限码），供角色管理按模块 / 功能勾选权限。

    权限码口径取 `platform:role:read` 而非 `platform:permission:read`：
    该树只服务于「角色管理」勾选权限，跟随角色读权限，避免出现
    「有角色管理权、却因缺权限目录读权而整个角色页报错」的口径不一致。

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
) -> Any:
    repo = ApiBindingRepository()
    bindings = await repo.list_bindings(db)
    return build_response(data=[ApiBindingResponse.model_validate(b).model_dump() for b in bindings])


# ── 授权管理 ──────────────────────────────────────────────────────


@router.get("/departments", response_model=DepartmentOptionListResponse)
async def list_department_options(
    ctx: PermissionContext = Depends(require_permission("platform:grant:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """授权管理「数据范围」选部门用的选项（hr.departments.code + name）。

    数据源是 hr.departments（部门唯一真理来源），通过 hr public_api 只读获取，
    避免在权限模块里直接 import hr 的模型。
    """
    from app.modules.hr.public_api import list_all_departments

    departments = await list_all_departments(db)
    data = [DepartmentOption(code=d.code, name=d.name) for d in departments if d.is_deleted is False]
    return build_response(data=data)


@router.get("/grants", response_model=GrantListResponse)
async def list_grants(
    user_id: uuid.UUID | None = Query(None),
    ctx: PermissionContext = Depends(require_permission("platform:grant:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
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
) -> Any:
    if payload.user_id == ctx.user.id:
        raise ForbiddenException("不能给自己授权")

    role = await get_role(db, payload.role_id)
    if role is None:
        raise NotFoundException("角色")

    # 超管保护 + 防越级：目标账号层级校验 + 授出角色不能超出操作者权限范围
    target_user = (await db.execute(select(User).where(User.id == payload.user_id))).scalar_one_or_none()
    if target_user is None:
        raise NotFoundException("用户")
    await guard_manage_target(db, actor=ctx.user, target=target_user)
    await assert_actor_can_grant_role(db, actor=ctx.user, role=role)

    _validate_scope(payload.scope_type, payload.scope_dept_codes)
    await _validate_department_codes(db, payload.scope_dept_codes)
    await assert_actor_can_grant_scope(
        db,
        actor=ctx.user,
        scope_type=payload.scope_type,
        scope_dept_codes=payload.scope_dept_codes,
    )

    grant_repo = GrantRepository()
    grant = await grant_repo.create_grant(
        db,
        user_id=payload.user_id,
        role_id=payload.role_id,
        scope_type=payload.scope_type,
        scope_dept_codes=payload.scope_dept_codes,
        granted_by=ctx.user.id,
    )
    await record_audit_log(
        db,
        user=ctx.user,
        action="grant.create",
        resource_type="grant",
        resource_id=grant.id,
        new_value={
            "user_id": str(payload.user_id),
            "role_code": role.code,
            "scope_type": payload.scope_type,
            "scope_dept_codes": payload.scope_dept_codes,
        },
    )
    await db.commit()
    await _evict_user_cache(grant.user_id)

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
) -> Any:
    grant_repo = GrantRepository()
    grant = await grant_repo.get_grant(db, grant_id)
    if grant is None:
        raise NotFoundException("授权")

    guard_self_escalation(ctx.user.id, grant)

    target_user = (await db.execute(select(User).where(User.id == grant.user_id))).scalar_one_or_none()
    if target_user is not None:
        await guard_manage_target(db, actor=ctx.user, target=target_user, resource_label="授权")

    if payload.scope_type is not None:
        _validate_scope(payload.scope_type, payload.scope_dept_codes)
        await _validate_department_codes(db, payload.scope_dept_codes)
        await assert_actor_can_grant_scope(
            db,
            actor=ctx.user,
            scope_type=payload.scope_type,
            scope_dept_codes=payload.scope_dept_codes,
        )
        grant.scope_type = payload.scope_type
        grant.scope_dept_codes = payload.scope_dept_codes
    if payload.status is not None:
        grant.status = payload.status
        grant.version += 1

    await record_audit_log(
        db,
        user=ctx.user,
        action="grant.update",
        resource_type="grant",
        resource_id=grant.id,
        new_value={
            "scope_type": payload.scope_type,
            "scope_dept_codes": payload.scope_dept_codes,
            "status": payload.status,
        },
    )
    await db.commit()
    await _evict_user_cache(grant.user_id)

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
) -> Any:
    grant_repo = GrantRepository()
    grant = await grant_repo.get_grant(db, grant_id)
    if grant is None:
        raise NotFoundException("授权")

    guard_self_escalation(ctx.user.id, grant)

    target_user = (await db.execute(select(User).where(User.id == grant.user_id))).scalar_one_or_none()
    if target_user is not None:
        await guard_manage_target(db, actor=ctx.user, target=target_user, resource_label="授权")

    await guard_last_superadmin(db, grant)

    role = await get_role(db, grant.role_id)
    await record_audit_log(
        db,
        user=ctx.user,
        action="grant.delete",
        resource_type="grant",
        resource_id=grant.id,
        old_value={
            "user_id": str(grant.user_id),
            "role_code": role.code if role else None,
            "scope_type": grant.scope_type,
        },
    )
    grant.is_deleted = True
    await db.commit()
    await _evict_user_cache(grant.user_id)
    return build_response()


# ── 当前用户权限 ──────────────────────────────────────────────────


@router.get("/my-permissions", response_model=MyPermissionsResponse)
async def my_permissions(
    user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    is_super = await is_superuser_with_cache(db, user)
    codes = await effective_permission_codes(db, user)
    return build_response(data=MyPermissionsData(permissions=sorted(codes), is_superuser=is_super))


@router.get("/preview/{user_id}", response_model=MyPermissionsResponse)
async def preview_user_access(
    user_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("platform:grant:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """预览某用户的生效权限（授权管理「生效预览」用）：返回权限码集合 + 是否超管。

    口径与 `my-permissions` 完全一致（超管返回全部权限码），只是针对任意目标用户。
    """
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if target is None:
        raise NotFoundException("用户")

    is_super = await is_superuser_with_cache(db, target)
    codes = await effective_permission_codes(db, target)
    return build_response(data=MyPermissionsData(permissions=sorted(codes), is_superuser=is_super))


# ── 工具 ──────────────────────────────────────────────────────────


def _validate_scope(scope_type: str, scope_dept_codes: list[str] | None) -> None:
    if scope_type in ("department", "department_and_children") and not scope_dept_codes:
        raise BadRequestException("指定部门范围时必须提供部门编码列表")


async def _validate_department_codes(db: AsyncSession, scope_dept_codes: list[str] | None) -> None:
    """校验数据范围里的部门编码在 hr.departments 中存在（纵深防御，防绕过前端直接调 API）。"""
    if not scope_dept_codes:
        return
    from app.modules.hr.public_api import list_all_departments

    departments = await list_all_departments(db)
    valid = {d.code for d in departments if d.is_deleted is False}
    invalid = [c for c in scope_dept_codes if c not in valid]
    if invalid:
        raise BadRequestException(f"部门编码不存在：{', '.join(invalid)}")
