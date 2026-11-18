"""权限管理 API。

挂载前缀：/api/v1/permission（见 api/router.py）。
所有管理接口本身受权限保护（platform:* 权限码）。
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import (
    PermissionContext,
    require_any_permission,
    require_assignment_admin,
    require_current_user,
    require_module_management,
    require_permission,
    require_role_catalog_read,
)
from app.core.exceptions import BadRequestException, DuplicateException, ForbiddenException, NotFoundException
from app.core.response import ApiResponse, build_response
from app.platform.audit.service import record_audit_log
from app.platform.identity.models import User
from app.platform.permission.cache import evict_user_permission_cache
from app.platform.permission.models import (
    GRANT_ACTIVE,
    Permission,
    Role,
    UserRoleGrant,
)
from app.platform.permission.registry import PERMISSIONS_BY_CODE
from app.platform.permission.repository import (
    ApiBindingRepository,
    GrantRepository,
    PermissionRepository,
    RoleRepository,
)
from app.platform.permission.schemas import (
    ApiBindingListResponse,
    ApiBindingResponse,
    BatchFailure,
    BatchResultApiResponse,
    BatchResultData,
    DepartmentOption,
    DepartmentOptionListResponse,
    GrantBatchCreate,
    GrantCreate,
    GrantDetailApiResponse,
    GrantListResponse,
    GrantResponse,
    GrantUpdate,
    IdsBatchRequest,
    MessageApiResponse,
    ModuleAdminAssignRequest,
    ModuleAdminGroup,
    ModuleAdminListResponse,
    ModuleAdminUser,
    MyPermissionsData,
    MyPermissionsResponse,
    PermissionApiBindingItem,
    PermissionApiBindingListResponse,
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
    StatusBatchRequest,
    UserAccessData,
    UserAccessDisableData,
    UserAccessDisableResponse,
    UserAccessItem,
    UserAccessResponse,
)
from app.platform.permission.service.authorization import is_superuser_with_cache
from app.platform.permission.service.catalog import (
    build_api_binding_items,
    build_permission_tree,
    count_permission_leaves,
)
from app.platform.permission.service.delegation import (
    MANAGE_ENTRY_SUFFIX,
    assert_can_create_role,
    assert_can_edit_role,
    assert_job_role_permissions,
    assert_module_manageable,
    assert_no_duplicate_grant,
    assert_role_permissions_subset,
    assert_target_role_operable,
    is_platform_admin,
    resolve_module_scope,
)
from app.platform.permission.service.description import (
    action_label,
    build_resource_label,
    module_label,
    resource_definitions,
)
from app.platform.permission.service.management import (
    assert_actor_can_grant_role,
    assert_actor_can_grant_scope,
    effective_permission_codes,
    get_role,
    guard_last_superadmin,
    guard_manage_target,
    guard_self_escalation,
    reset_role_to_default,
)
from app.platform.permission.service.role_code import next_role_code
from app.shared.module_registry import BUSINESS_MODULES

logger = logging.getLogger(__name__)

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
    module_code: str | None = Query(None, description="按模块过滤（模块负责人/管理人只能查本模块）"),
    ctx: PermissionContext = Depends(require_module_management()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    role_repo = RoleRepository()
    scope = await resolve_module_scope(db, ctx.user)
    # 显式请求别的模块 → 403（不是空列表）
    if module_code is not None:
        assert_module_manageable(scope, module_code)

    roles = await role_repo.list_roles(db)
    data = []
    for role in roles:
        # 系统管理员角色只对系统管理员可见
        if (role.is_superuser or role.role_type == "system") and not scope.is_system_admin:
            continue
        if not scope.can_manage(role.module_code):
            continue
        if module_code is not None and role.module_code != module_code:
            continue
        codes = await role_repo.list_role_permission_codes(db, role.id)
        data.append(
            RoleDetailResponse(
                id=role.id,
                code=role.code,
                name=role.name,
                category=role.category,
                role_type=role.role_type,
                module_code=role.module_code,
                description=role.description,
                is_builtin=role.is_builtin,
                is_superuser=role.is_superuser,
                status=role.status,
                sync_locked=role.sync_locked,
                permission_codes=codes,
            )
        )
    return build_response(data=data)


@router.post("/roles", response_model=RoleDetailApiResponse)
async def create_role(
    payload: RoleCreate,
    ctx: PermissionContext = Depends(require_module_management()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    role_repo = RoleRepository()
    # 编码可由后端自动生成，只有显式传码时才做「已存在」前置校验
    explicit_code = (payload.code or "").strip() or None
    if explicit_code is not None:
        existing = await role_repo.get_role_by_code(db, explicit_code)
        if existing is not None:
            raise DuplicateException("角色编码", explicit_code)

    if payload.category == "module" and not payload.module_code:
        raise BadRequestException("模块角色必须指定模块编码")

    unknown = [c for c in payload.permission_codes if c not in PERMISSIONS_BY_CODE]
    if unknown:
        raise BadRequestException(f"未知权限码：{', '.join(unknown)}")

    # 委派守卫：模块作用域 + 编码格式/保留字 + 权限码范围（R5/R6/R7）
    scope = await resolve_module_scope(db, ctx.user)
    await assert_role_permissions_subset(db, ctx.user, payload.permission_codes)

    # 编码由后端生成（界面不暴露）；兼容显式传码的脚本 / E2E 调用。
    # 并发创建靠 roles.code 唯一约束兜底，冲突时重算重试。
    role: Role | None = None
    for attempt in range(1, 4):
        code = explicit_code or await next_role_code(db, payload.module_code)
        assert_can_create_role(scope, payload.module_code, code, payload.permission_codes)
        candidate = Role(
            code=code,
            name=payload.name,
            category=payload.category,
            module_code=payload.module_code,
            description=payload.description,
            is_builtin=False,
            is_superuser=False,
            status=GRANT_ACTIVE,
        )
        db.add(candidate)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            if explicit_code:
                raise BadRequestException(f"角色编码已存在：{explicit_code}") from None
            logger.warning(
                "角色编码生成冲突，重新生成",
                extra={"role_code": code, "attempt": attempt},
            )
            continue
        role = candidate
        break

    if role is None:
        raise BadRequestException("角色编码生成冲突，请重试")
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
            role_type=role.role_type,
            module_code=role.module_code,
            description=role.description,
            is_builtin=role.is_builtin,
            is_superuser=role.is_superuser,
            status=role.status,
            sync_locked=role.sync_locked,
            permission_codes=codes,
        )
    )


@router.post("/roles/{role_id}/reset-default", response_model=RoleDetailApiResponse)
async def reset_role_permissions(
    role_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_module_management()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """把内置角色的权限恢复为代码注册表的装配值，并重新纳入启动自动扩量。"""
    role_repo = RoleRepository()
    role = await role_repo.get_role(db, role_id)
    if role is None:
        raise NotFoundException("角色")

    scope = await resolve_module_scope(db, ctx.user)
    if not scope.is_system_admin:
        raise ForbiddenException("只有系统管理员可以恢复内置角色的默认权限")

    count = await reset_role_to_default(db, role)
    await record_audit_log(
        db,
        user=ctx.user,
        action="role.reset_default",
        resource_type="role",
        resource_id=role.id,
        new_value={"code": role.code, "permission_count": count},
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
            role_type=role.role_type,
            module_code=role.module_code,
            description=role.description,
            is_builtin=role.is_builtin,
            is_superuser=role.is_superuser,
            status=role.status,
            sync_locked=role.sync_locked,
            permission_codes=codes,
        )
    )


@router.put("/roles/{role_id}", response_model=RoleDetailApiResponse)
async def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdate,
    ctx: PermissionContext = Depends(require_module_management()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    role_repo = RoleRepository()
    role = await role_repo.get_role(db, role_id)
    if role is None:
        raise NotFoundException("角色")

    # 委派守卫：系统管理员可改内置角色权限；岗位角色限本模块（R2/R5）
    scope = await resolve_module_scope(db, ctx.user)
    assert_can_edit_role(scope, role, allow_builtin=True)

    # 内置角色（模块负责人 / 模块管理员）的权限允许超出模块业务码（例如保留管理入口），
    # 其余角色仍按岗位角色规则校验
    editing_builtin = role.is_builtin

    if payload.permission_codes is not None:
        if not editing_builtin:
            assert_job_role_permissions(role.module_code or "", payload.permission_codes)
        unknown = [c for c in payload.permission_codes if c not in PERMISSIONS_BY_CODE]
        if unknown:
            raise BadRequestException(f"未知权限码：{', '.join(unknown)}")
        await assert_role_permissions_subset(db, ctx.user, payload.permission_codes)
        # 防间接提权：不能修改自己所属角色的权限（保守策略）；
        # 系统管理员编辑内置角色属受控场景（改的是自己的管理能力），放行
        if not (editing_builtin and scope.is_system_admin):
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
        # 手工接管：内置角色一旦被人工改动，就退出启动时的自动扩量
        if editing_builtin:
            role.sync_locked = True

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
            role_type=role.role_type,
            module_code=role.module_code,
            description=role.description,
            is_builtin=role.is_builtin,
            is_superuser=role.is_superuser,
            status=role.status,
            sync_locked=role.sync_locked,
            permission_codes=codes,
        )
    )


@router.delete("/roles/{role_id}", response_model=MessageApiResponse)
async def delete_role(
    role_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_module_management()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    role_repo = RoleRepository()
    role = await role_repo.get_role(db, role_id)
    if role is None:
        raise NotFoundException("角色")

    scope = await resolve_module_scope(db, ctx.user)
    assert_can_edit_role(scope, role)

    # R8：删除角色时其授权行一并停用（可恢复），避免留下孤儿授权行
    disabled = await role_repo.disable_grants_for_role(db, role.id)
    await role_repo.soft_delete_role(db, role)
    await record_audit_log(
        db,
        user=ctx.user,
        action="role.delete",
        resource_type="role",
        resource_id=role.id,
        old_value={"code": role.code, "name": role.name, "disabled_grants": disabled},
    )
    await db.commit()
    await _evict_cache_for_role(db, role.id)
    return build_response()


@router.post(
    "/roles/batch-status",
    response_model=BatchResultApiResponse,
    summary="批量启用 / 停用角色",
)
async def batch_role_status(
    payload: StatusBatchRequest,
    ctx: PermissionContext = Depends(require_permission("platform:role:manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """逐条校验并汇总结果。

    - 内置角色不可修改状态（与单条更新一致）；
    - 状态已一致的按幂等处理（计入成功、不写审计）；
    - 失败项不影响其他角色，返回原因。
    """
    role_repo = RoleRepository()
    succeeded: list[str] = []
    failed: list[BatchFailure] = []
    changed: list[uuid.UUID] = []

    for role_id in dict.fromkeys(payload.ids):
        role = await role_repo.get_role(db, role_id)
        if role is None:
            failed.append(BatchFailure(key=str(role_id), reason="角色不存在"))
            continue
        if role.is_builtin:
            failed.append(BatchFailure(key=str(role.id), label=role.name, reason="内置角色不可修改状态"))
            continue
        if role.status == payload.status:
            succeeded.append(str(role.id))
            continue

        role.status = payload.status
        changed.append(role.id)
        await record_audit_log(
            db,
            user=ctx.user,
            action="role.update",
            resource_type="role",
            resource_id=role.id,
            new_value={"name": role.name, "status": payload.status, "batch": True},
        )
        succeeded.append(str(role.id))

    await db.commit()
    for role_id in changed:
        await _evict_cache_for_role(db, role_id)
    return build_response(data=BatchResultData(succeeded=succeeded, failed=failed).model_dump())


@router.post(
    "/roles/batch-delete",
    response_model=BatchResultApiResponse,
    summary="批量删除角色",
)
async def batch_delete_roles(
    payload: IdsBatchRequest,
    ctx: PermissionContext = Depends(require_permission("platform:role:manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """逐条软删除；内置角色与超级管理员角色一律跳过并返回原因。"""
    role_repo = RoleRepository()
    succeeded: list[str] = []
    failed: list[BatchFailure] = []
    changed: list[uuid.UUID] = []

    for role_id in dict.fromkeys(payload.ids):
        role = await role_repo.get_role(db, role_id)
        if role is None:
            failed.append(BatchFailure(key=str(role_id), reason="角色不存在"))
            continue
        if role.is_builtin:
            failed.append(BatchFailure(key=str(role.id), label=role.name, reason="内置角色不可删除"))
            continue
        if role.is_superuser:
            failed.append(BatchFailure(key=str(role.id), label=role.name, reason="超级管理员角色不可删除"))
            continue

        await role_repo.soft_delete_role(db, role)
        changed.append(role.id)
        await record_audit_log(
            db,
            user=ctx.user,
            action="role.delete",
            resource_type="role",
            resource_id=role.id,
            old_value={"code": role.code, "name": role.name, "batch": True},
        )
        succeeded.append(str(role.id))

    await db.commit()
    for role_id in changed:
        await _evict_cache_for_role(db, role_id)
    return build_response(data=BatchResultData(succeeded=succeeded, failed=failed).model_dump())


# ── 权限目录 ──────────────────────────────────────────────────────


def _permission_response(permission: Permission) -> dict[str, Any]:
    """DB 权限行转响应，并补注册表派生的中文展示字段（目录页「模块/资源/动作」三列）。

    库里可能存在注册表已退役的历史权限码，此时三个中文列保持 None，前端回退英文原值。
    """
    item = PermissionResponse.model_validate(permission)
    definition = PERMISSIONS_BY_CODE.get(permission.code)
    if definition is None:
        return item.model_dump()
    return item.model_copy(
        update={
            "module_label": module_label(definition.module),
            "resource_label": build_resource_label(
                definition.module,
                definition.resource,
                resource_definitions(definition.module, definition.resource),
            ),
            "action_label": action_label(definition.action),
        }
    ).model_dump()


@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    ctx: PermissionContext = Depends(require_permission("platform:permission:read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    repo = PermissionRepository()
    perms = await repo.list_permissions(db)
    return build_response(data=[_permission_response(p) for p in perms])


@router.get("/tree", response_model=PermissionTreeResponse)
async def get_permission_tree(
    ctx: PermissionContext = Depends(require_role_catalog_read()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """权限目录树（模块 → 资源 → 权限码），供角色管理按模块 / 功能勾选权限。

    准入取 `require_role_catalog_read()`：除 `platform:role:read` / `platform:role:manage`
    外，也放行模块负责人与模块管理员（他们只持有本模块业务码 + `{module}:admin:read`，
    缺少 `platform:role:read`；否则模块配置页「新建角色」的权限树会 403 成空树）。

    按模块管理入口进入的操作者只返回其可管理模块的子树；平台级角色管理员返回全量。
    纯注册表数据、不查库，因此权限表未迁移时也可正常返回。
    """
    tree, total_permissions = build_permission_tree()
    if ctx.permission_code.endswith(MANAGE_ENTRY_SUFFIX):
        scope = await resolve_module_scope(db, ctx.user)
        tree = [node for node in tree if node.get("code") in scope.modules]
        total_permissions = count_permission_leaves(tree)
    data = PermissionTreeData(
        tree=[PermissionTreeNode(**node) for node in tree],
        total_permissions=total_permissions,
        total_modules=len(tree),
    )
    return build_response(data=data.model_dump())


@router.get("/permissions/{code}/api-bindings", response_model=PermissionApiBindingListResponse)
async def list_permission_api_bindings(
    code: str,
    ctx: PermissionContext = Depends(require_role_catalog_read()),
) -> ApiResponse:
    """单个权限码绑定的接口清单，供角色管理勾选权限时按需展开。

    准入与 `/tree` 一致取 `require_role_catalog_read()`：这份清单只服务于
    「勾这个权限会放开哪些接口」，角色管理员通常没有 `platform:api-binding:read`，
    复用登记簿端点会 403。按模块管理入口进入的操作者只能查本模块的权限码。

    纯注册表数据、不查库，因此权限表未迁移时也可正常返回。
    """
    if code not in PERMISSIONS_BY_CODE:
        raise NotFoundException("权限码", code)
    if ctx.permission_code.endswith(MANAGE_ENTRY_SUFFIX):
        module_code = ctx.permission_code.split(":", 1)[0]
        if PERMISSIONS_BY_CODE[code].module != module_code:
            raise ForbiddenException("只能查看本模块权限码绑定的接口")
    items = [PermissionApiBindingItem(**item) for item in build_api_binding_items(code)]
    return build_response(data=[item.model_dump() for item in items])


# ── 接口绑定登记簿 ────────────────────────────────────────────────


@router.get("/api-bindings", response_model=ApiBindingListResponse)
async def list_api_bindings(
    ctx: PermissionContext = Depends(require_permission("platform:api-binding:read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    repo = ApiBindingRepository()
    bindings = await repo.list_bindings(db)
    return build_response(data=[ApiBindingResponse.model_validate(b).model_dump() for b in bindings])


# ── 授权管理 ──────────────────────────────────────────────────────


@router.get("/departments", response_model=DepartmentOptionListResponse)
async def list_department_options(
    # 只有 grant:manage 的管理员也要能用授权表单选部门
    ctx: PermissionContext = Depends(require_any_permission("platform:grant:read", "platform:grant:manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
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
    module_code: str | None = Query(None, description="按模块过滤（模块负责人/管理人只能查本模块）"),
    ctx: PermissionContext = Depends(require_module_management()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    scope = await resolve_module_scope(db, ctx.user)
    if module_code is not None:
        assert_module_manageable(scope, module_code)

    stmt = (
        select(
            UserRoleGrant,
            Role.code,
            Role.name,
            User.name,
            User.username,
            User.avatar_thumb,
            User.avatar_url,
        )
        .join(Role, Role.id == UserRoleGrant.role_id)
        .outerjoin(User, User.id == UserRoleGrant.user_id)
        .where(UserRoleGrant.is_deleted == False)  # noqa: E712
        .order_by(UserRoleGrant.created_at.desc())
    )
    if not scope.is_system_admin:
        stmt = stmt.where(Role.module_code.in_(sorted(scope.modules)))
    if user_id is not None:
        stmt = stmt.where(UserRoleGrant.user_id == user_id)
    if module_code is not None:
        stmt = stmt.where(Role.module_code == module_code)
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
            username=username,
            avatar_url=avatar_thumb or avatar_url,
        )
        for g, role_code, role_name, user_name, username, avatar_thumb, avatar_url in rows
    ]
    return build_response(data=data)


@router.post("/grants", response_model=GrantDetailApiResponse)
async def create_grant(
    payload: GrantCreate,
    ctx: PermissionContext = Depends(require_module_management()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    if payload.user_id == ctx.user.id:
        raise ForbiddenException("不能给自己授权")

    role = await get_role(db, payload.role_id)
    if role is None:
        raise NotFoundException("角色")

    # 委派守卫：内置管理角色仅系统管理员可授（R2）；岗位角色限本模块（R5）
    scope = await resolve_module_scope(db, ctx.user)
    assert_target_role_operable(scope, role)
    if not role.is_superuser:
        assert_module_manageable(scope, role.module_code)

    # #219：统一人员选择器返回 hr.employee_profiles.id，而授权键仍是
    # identity.users.id；查不到账号时按 HR 档案按需建号（登录前授权）。
    from app.platform.identity.public_api import resolve_person_user_id

    target_user_id = await resolve_person_user_id(db, payload.user_id)
    if target_user_id is None:
        raise NotFoundException("用户")
    if target_user_id == ctx.user.id:
        raise ForbiddenException("不能给自己授权")

    await assert_no_duplicate_grant(db, target_user_id, role.id)
    # 数据范围当前休眠：模块负责人/管理人授权一律 all，不接受自定义范围
    if not scope.is_system_admin and payload.scope_type != "all":
        raise ForbiddenException("模块内授权不支持自定义数据范围")

    # 平台级管理员（系统管理员 / 既有 grant:manage 账号）走原有分级校验；
    # 模块负责人/管理人只在本模块作业，范围已由 R2/R5/R6 限定，不再做子集比较
    # （否则"给员工开偏差查看权限"会因为他自己没有该权限码而被拒）。
    if await is_platform_admin(db, ctx.user):
        target_user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one()
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
        user_id=target_user_id,
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


@router.post(
    "/grants/batch-create",
    response_model=BatchResultApiResponse,
    summary="批量授权（多用户 × 多角色）",
)
async def batch_create_grants(
    payload: GrantBatchCreate,
    ctx: PermissionContext = Depends(require_permission("platform:grant:manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """一次给多个用户授予多个角色，统一套用同一个数据范围。

    逐对 (用户, 角色) 复用单条授权护栏：不能给自己授权、目标账号层级校验、
    授出角色不能超出操作者权限范围；数据范围在入口处统一校验一次。

    - 已存在同用户同角色的有效授权按幂等处理：计入 succeeded、不重复插入、不写审计。
    - 真正的拒绝项（用户不可用 / 角色不可用 / 越级）逐条返回原因，不影响其他组合。
    """
    from app.platform.identity.public_api import resolve_person_user_id

    _validate_scope(payload.scope_type, payload.scope_dept_codes)
    await _validate_department_codes(db, payload.scope_dept_codes)
    await assert_actor_can_grant_scope(
        db,
        actor=ctx.user,
        scope_type=payload.scope_type,
        scope_dept_codes=payload.scope_dept_codes,
    )

    succeeded: list[str] = []
    failed: list[BatchFailure] = []

    # 1) 角色预取 + 授出权限校验（同一角色与目标用户无关，只判一次）
    roles: dict[uuid.UUID, Role] = {}
    role_errors: dict[uuid.UUID, tuple[str, str | None]] = {}
    for role_id in dict.fromkeys(payload.role_ids):
        role = await get_role(db, role_id)
        if role is None:
            role_errors[role_id] = ("角色不存在或已删除", None)
            continue
        try:
            await assert_actor_can_grant_role(db, actor=ctx.user, role=role)
        except ForbiddenException as exc:
            role_errors[role_id] = (exc.message or "无权授予该角色", role.name)
            continue
        roles[role_id] = role

    # 角色不可用时，所有用户都无法拿到该角色：只报一条，避免 N 份重复原因
    for role_id, (reason, label) in role_errors.items():
        failed.append(BatchFailure(key=str(role_id), label=label, reason=reason))

    # 2) 用户预取：人员 id → 账号 id（未建号的 HR 档案按需建号，逻辑与单条授权一致）
    targets: dict[uuid.UUID, User] = {}
    user_errors: dict[uuid.UUID, str] = {}
    for raw_id in dict.fromkeys(payload.user_ids):
        resolved_id = await resolve_person_user_id(db, raw_id)
        if resolved_id is None:
            user_errors[raw_id] = "用户不存在"
            continue
        if resolved_id == ctx.user.id:
            user_errors[raw_id] = "不能给自己授权"
            continue
        target = (await db.execute(select(User).where(User.id == resolved_id))).scalar_one_or_none()
        if target is None:
            user_errors[raw_id] = "用户不存在"
            continue
        try:
            await guard_manage_target(db, actor=ctx.user, target=target, resource_label="授权")
        except ForbiddenException as exc:
            user_errors[raw_id] = exc.message or "无权操作该账号"
            continue
        targets[raw_id] = target

    # 3) 已存在的有效授权：一次 IN 查询，命中的组合按幂等跳过（复用原授权 id）
    existing_ids: dict[tuple[uuid.UUID, uuid.UUID], uuid.UUID] = {}
    target_ids = {user.id for user in targets.values()}
    if target_ids and roles:
        stmt = select(UserRoleGrant.id, UserRoleGrant.user_id, UserRoleGrant.role_id).where(
            UserRoleGrant.user_id.in_(target_ids),
            UserRoleGrant.role_id.in_(set(roles)),
            UserRoleGrant.status == GRANT_ACTIVE,
            UserRoleGrant.is_deleted == False,  # noqa: E712
        )
        for grant_id, user_id, role_id in (await db.execute(stmt)).all():
            existing_ids[(user_id, role_id)] = grant_id

    # 4) 笛卡尔积：创建 / 幂等跳过 / 逐条记录失败
    grant_repo = GrantRepository()
    affected_users: set[uuid.UUID] = set()
    handled: set[tuple[uuid.UUID, uuid.UUID]] = set()

    for raw_id in dict.fromkeys(payload.user_ids):
        target = targets.get(raw_id)
        if target is None:
            failed.append(BatchFailure(key=str(raw_id), reason=user_errors.get(raw_id, "用户不可用")))
            continue
        for role_id in dict.fromkeys(payload.role_ids):
            role = roles.get(role_id)
            if role is None:
                continue  # 角色级失败已在上方统一记录
            pair = (target.id, role_id)
            if pair in handled:
                continue  # 同一账号被不同人员引用重复传入时只处理一次
            handled.add(pair)

            existing_id = existing_ids.get(pair)
            if existing_id is not None:
                succeeded.append(str(existing_id))
                continue

            grant = await grant_repo.create_grant(
                db,
                user_id=target.id,
                role_id=role_id,
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
                    "user_id": str(target.id),
                    "role_code": role.code,
                    "scope_type": payload.scope_type,
                    "scope_dept_codes": payload.scope_dept_codes,
                    "batch": True,
                },
            )
            succeeded.append(str(grant.id))
            affected_users.add(target.id)

    await db.commit()
    for user_id in affected_users:
        await _evict_user_cache(user_id)

    return build_response(data=BatchResultData(succeeded=succeeded, failed=failed).model_dump())


@router.put("/grants/{grant_id}", response_model=GrantDetailApiResponse)
async def update_grant(
    grant_id: uuid.UUID,
    payload: GrantUpdate,
    ctx: PermissionContext = Depends(require_module_management()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    grant_repo = GrantRepository()
    grant = await grant_repo.get_grant(db, grant_id)
    if grant is None:
        raise NotFoundException("授权")

    guard_self_escalation(ctx.user.id, grant)

    grant_role = await get_role(db, grant.role_id)
    if grant_role is not None:
        scope = await resolve_module_scope(db, ctx.user)
        assert_target_role_operable(scope, grant_role)
        if not grant_role.is_superuser:
            assert_module_manageable(scope, grant_role.module_code)
        if not scope.is_system_admin and payload.scope_type not in (None, "all"):
            raise ForbiddenException("模块内授权不支持自定义数据范围")

    if await is_platform_admin(db, ctx.user):
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
    ctx: PermissionContext = Depends(require_module_management()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    grant_repo = GrantRepository()
    grant = await grant_repo.get_grant(db, grant_id)
    if grant is None:
        raise NotFoundException("授权")

    guard_self_escalation(ctx.user.id, grant)

    grant_role = await get_role(db, grant.role_id)
    if grant_role is not None:
        scope = await resolve_module_scope(db, ctx.user)
        assert_target_role_operable(scope, grant_role)
        if not grant_role.is_superuser:
            assert_module_manageable(scope, grant_role.module_code)

    if await is_platform_admin(db, ctx.user):
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


@router.post(
    "/grants/batch-status",
    response_model=BatchResultApiResponse,
    summary="批量启用 / 停用授权",
)
async def batch_grant_status(
    payload: StatusBatchRequest,
    ctx: PermissionContext = Depends(require_permission("platform:grant:manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """逐条复用单条护栏：不能改自己的授权、不能越级、不能停用最后一个超管授权。

    每停用一条立即 flush，避免「同批停用两条超管授权」时计数看不到前面的变更。
    """
    grant_repo = GrantRepository()
    succeeded: list[str] = []
    failed: list[BatchFailure] = []
    affected_users: set[uuid.UUID] = set()

    for grant_id in dict.fromkeys(payload.ids):
        grant = await grant_repo.get_grant(db, grant_id)
        if grant is None:
            failed.append(BatchFailure(key=str(grant_id), reason="授权不存在"))
            continue

        try:
            guard_self_escalation(ctx.user.id, grant)
            target_user = (await db.execute(select(User).where(User.id == grant.user_id))).scalar_one_or_none()
            if target_user is not None:
                await guard_manage_target(db, actor=ctx.user, target=target_user, resource_label="授权")
            if payload.status != GRANT_ACTIVE:
                await guard_last_superadmin(db, grant)
        except ForbiddenException as exc:
            failed.append(BatchFailure(key=str(grant.id), reason=exc.message))
            continue

        if grant.status == payload.status:
            succeeded.append(str(grant.id))
            continue

        grant.status = payload.status
        grant.version += 1
        # flush 让同批后续的「最后一个超管」判断能看到本次停用
        await db.flush()
        affected_users.add(grant.user_id)
        await record_audit_log(
            db,
            user=ctx.user,
            action="grant.update",
            resource_type="grant",
            resource_id=grant.id,
            new_value={"status": payload.status, "batch": True},
        )
        succeeded.append(str(grant.id))

    await db.commit()
    for user_id in affected_users:
        await _evict_user_cache(user_id)
    return build_response(data=BatchResultData(succeeded=succeeded, failed=failed).model_dump())


@router.post(
    "/grants/batch-delete",
    response_model=BatchResultApiResponse,
    summary="批量删除授权",
)
async def batch_delete_grants(
    payload: IdsBatchRequest,
    ctx: PermissionContext = Depends(require_permission("platform:grant:manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """逐条软删除；自己 / 越级 / 最后一个超管的授权跳过并返回原因。"""
    grant_repo = GrantRepository()
    succeeded: list[str] = []
    failed: list[BatchFailure] = []
    affected_users: set[uuid.UUID] = set()

    for grant_id in dict.fromkeys(payload.ids):
        grant = await grant_repo.get_grant(db, grant_id)
        if grant is None:
            failed.append(BatchFailure(key=str(grant_id), reason="授权不存在"))
            continue

        try:
            guard_self_escalation(ctx.user.id, grant)
            target_user = (await db.execute(select(User).where(User.id == grant.user_id))).scalar_one_or_none()
            if target_user is not None:
                await guard_manage_target(db, actor=ctx.user, target=target_user, resource_label="授权")
            await guard_last_superadmin(db, grant)
        except ForbiddenException as exc:
            failed.append(BatchFailure(key=str(grant.id), reason=exc.message))
            continue

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
                "batch": True,
            },
        )
        grant.is_deleted = True
        # flush 让同批后续的「最后一个超管」判断能看到本次删除
        await db.flush()
        affected_users.add(grant.user_id)
        succeeded.append(str(grant.id))

    await db.commit()
    for user_id in affected_users:
        await _evict_user_cache(user_id)
    return build_response(data=BatchResultData(succeeded=succeeded, failed=failed).model_dump())


# ── 当前用户权限 ──────────────────────────────────────────────────


@router.get("/my-permissions", response_model=MyPermissionsResponse)
async def my_permissions(
    user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    is_super = await is_superuser_with_cache(db, user)
    codes = await effective_permission_codes(db, user)
    return build_response(data=MyPermissionsData(permissions=sorted(codes), is_superuser=is_super))


@router.get("/preview/{user_id}", response_model=MyPermissionsResponse)
async def preview_user_access(
    user_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_any_permission("platform:grant:read", "platform:grant:manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """预览某用户的生效权限（授权管理「生效预览」用）：返回权限码集合 + 是否超管。

    口径与 `my-permissions` 完全一致（超管返回全部权限码），只是针对任意目标用户。
    """
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if target is None:
        raise NotFoundException("用户")

    is_super = await is_superuser_with_cache(db, target)
    codes = await effective_permission_codes(db, target)
    return build_response(data=MyPermissionsData(permissions=sorted(codes), is_superuser=is_super))


# ── 模块负责人 / 模块管理员（系统管理员侧）─────────────────────────────

_MODULE_NAME_BY_CODE = {module.code: module.name for module in BUSINESS_MODULES}


@router.get("/module-admins", response_model=ModuleAdminListResponse)
async def list_module_admins(
    ctx: PermissionContext = Depends(require_assignment_admin()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """按模块列出负责人与管理人（含"未指派"空态所需的全部模块）。"""
    stmt = (
        select(UserRoleGrant, Role, User.name, User.username)
        .join(Role, Role.id == UserRoleGrant.role_id)
        .outerjoin(User, User.id == UserRoleGrant.user_id)
        .where(
            Role.role_type.in_(("head", "manager")),
            Role.is_deleted == False,  # noqa: E712
            UserRoleGrant.status == GRANT_ACTIVE,
            UserRoleGrant.is_deleted == False,  # noqa: E712
        )
        .order_by(Role.module_code, Role.role_type)
    )
    rows = (await db.execute(stmt)).all()

    groups = {
        module.code: ModuleAdminGroup(module_code=module.code, module_name=module.name) for module in BUSINESS_MODULES
    }
    for grant, role, name, username in rows:
        group = groups.get(role.module_code or "")
        if group is None:
            continue
        item = ModuleAdminUser(
            grant_id=grant.id,
            user_id=grant.user_id,
            name=name,
            username=username,
            role_code=role.code,
            role_type=role.role_type,
        )
        if role.role_type == "head":
            group.heads.append(item)
        elif role.role_type == "manager":
            group.managers.append(item)

    return build_response(data=list(groups.values()))


async def _resolve_assignment_role(db: AsyncSession, payload: ModuleAdminAssignRequest) -> Role:
    role_code = f"{payload.module_code}:{'head' if payload.role_type == 'head' else 'manager'}"
    role = await RoleRepository().get_role_by_code(db, role_code)
    if role is None:
        raise NotFoundException("模块内置角色")
    return role


@router.post("/module-admins", response_model=MessageApiResponse)
async def assign_module_admin(
    payload: ModuleAdminAssignRequest,
    ctx: PermissionContext = Depends(require_assignment_admin()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """指派模块负责人 / 模块管理员（仅系统管理员）。"""
    from app.platform.identity.public_api import resolve_person_user_id

    role = await _resolve_assignment_role(db, payload)
    target_user_id = await resolve_person_user_id(db, payload.user_id)
    if target_user_id is None:
        raise NotFoundException("用户")

    await assert_no_duplicate_grant(db, target_user_id, role.id)

    grant = await GrantRepository().create_grant(
        db,
        user_id=target_user_id,
        role_id=role.id,
        scope_type="all",
        scope_dept_codes=None,
        granted_by=ctx.user.id,
    )
    await record_audit_log(
        db,
        user=ctx.user,
        action="module_admin.assign",
        resource_type="grant",
        resource_id=grant.id,
        new_value={
            "module_code": payload.module_code,
            "role_code": role.code,
            "target_user_id": str(target_user_id),
        },
    )
    await db.commit()
    await _evict_user_cache(target_user_id)
    return build_response()


@router.post("/module-admins/remove", response_model=MessageApiResponse)
async def remove_module_admin(
    payload: ModuleAdminAssignRequest,
    ctx: PermissionContext = Depends(require_assignment_admin()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """移除模块负责人 / 模块管理员（仅系统管理员）。"""
    from app.platform.identity.public_api import resolve_person_user_id

    role = await _resolve_assignment_role(db, payload)
    target_user_id = await resolve_person_user_id(db, payload.user_id)
    if target_user_id is None:
        raise NotFoundException("用户")

    result = await db.execute(
        select(UserRoleGrant).where(
            UserRoleGrant.user_id == target_user_id,
            UserRoleGrant.role_id == role.id,
            UserRoleGrant.status == GRANT_ACTIVE,
            UserRoleGrant.is_deleted == False,  # noqa: E712
        )
    )
    grant = result.scalar_one_or_none()
    if grant is None:
        raise NotFoundException("授权")

    grant.is_deleted = True
    await record_audit_log(
        db,
        user=ctx.user,
        action="module_admin.remove",
        resource_type="grant",
        resource_id=grant.id,
        old_value={
            "module_code": payload.module_code,
            "role_code": role.code,
            "target_user_id": str(target_user_id),
        },
    )
    await db.commit()
    await _evict_user_cache(target_user_id)
    return build_response()


# ── 按人查权限（离职 / 调岗收权兜底）──────────────────────────────────


@router.get("/user-access/{user_id}", response_model=UserAccessResponse)
async def get_user_access(
    user_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_assignment_admin()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    from app.platform.identity.public_api import resolve_person_user_id

    resolved_id = await resolve_person_user_id(db, user_id)
    if resolved_id is None:
        raise NotFoundException("用户")
    user = (await db.execute(select(User).where(User.id == resolved_id))).scalar_one()

    stmt = (
        select(UserRoleGrant, Role)
        .join(Role, Role.id == UserRoleGrant.role_id)
        .where(
            UserRoleGrant.user_id == resolved_id,
            UserRoleGrant.is_deleted == False,  # noqa: E712
            Role.is_deleted == False,  # noqa: E712
        )
        .order_by(Role.module_code, Role.code)
    )
    rows = (await db.execute(stmt)).all()
    items = [
        UserAccessItem(
            grant_id=grant.id,
            role_id=role.id,
            role_code=role.code,
            role_name=role.name,
            role_type=role.role_type,
            module_code=role.module_code,
            status=grant.status,
        )
        for grant, role in rows
    ]
    return build_response(
        data=UserAccessData(
            user_id=resolved_id,
            name=user.name,
            username=user.username,
            is_superuser=any(item.role_type == "system" for item in items),
            items=items,
        )
    )


@router.post("/user-access/{user_id}/disable", response_model=UserAccessDisableResponse)
async def disable_user_access(
    user_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_assignment_admin()),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """停用某用户的全部模块授权（离职/调岗收权）。

    系统管理员授权不在此处处理：超管降级受「保底两人」约束，需单独操作。
    """
    from app.platform.identity.public_api import resolve_person_user_id

    resolved_id = await resolve_person_user_id(db, user_id)
    if resolved_id is None:
        raise NotFoundException("用户")

    stmt = (
        select(UserRoleGrant, Role)
        .join(Role, Role.id == UserRoleGrant.role_id)
        .where(
            UserRoleGrant.user_id == resolved_id,
            UserRoleGrant.status == GRANT_ACTIVE,
            UserRoleGrant.is_deleted == False,  # noqa: E712
            Role.is_deleted == False,  # noqa: E712
        )
    )
    rows = (await db.execute(stmt)).all()
    if any(role.role_type == "system" for _grant, role in rows):
        raise ForbiddenException("该账号持有系统管理员授权，请先在授权管理中单独移除")

    for grant, _role in rows:
        grant.status = "disabled"
        grant.version += 1
    await record_audit_log(
        db,
        user=ctx.user,
        action="user_access.disable_all",
        resource_type="user",
        resource_id=resolved_id,
        old_value={"disabled_grants": len(rows)},
    )
    await db.commit()
    await _evict_user_cache(resolved_id)
    return build_response(data=UserAccessDisableData(disabled=len(rows)))


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
