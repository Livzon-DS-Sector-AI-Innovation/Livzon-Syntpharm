from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.identity.models import (
    Department,
    FeishuCardAction,
    FeishuConfig,
    User,
)


class UserRepository:
    async def get_by_id(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                User.id == user_id,
                User.is_deleted == False,  # noqa: E712
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        session: AsyncSession,
        username: str,
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                func.lower(User.username) == username.lower(),
                User.is_deleted == False,  # noqa: E712
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_username_including_deleted(
        self,
        session: AsyncSession,
        username: str,
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                func.lower(User.username) == username.lower(),
            ),
        )
        return result.scalar_one_or_none()

    async def soft_delete_user(
        self,
        session: AsyncSession,
        user: User,
        *,
        operator_id: UUID | None = None,
    ) -> User:
        """软删除账号：标记删除并置禁用。

        物理删除不可行——`permission.user_role_grants.user_id` 等外键是 NOT NULL 且
        没有 ON DELETE 规则（PostgreSQL 默认 NO ACTION），删行会被数据库挡住。
        """
        user.is_deleted = True
        user.status = "disabled"
        if operator_id is not None:
            user.updated_by = operator_id
        await session.flush()
        return user

    async def get_by_login_identifier(
        self,
        session: AsyncSession,
        identifier: str,
    ) -> User | None:
        normalized = identifier.strip().lower()
        result = await session.execute(
            select(User).where(
                User.is_deleted == False,  # noqa: E712
                or_(
                    func.lower(User.username) == normalized,
                    func.lower(User.email) == normalized,
                    User.mobile == identifier,
                    User.employee_no == identifier,
                ),
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_feishu_open_id(
        self,
        session: AsyncSession,
        open_id: str,
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                User.feishu_open_id == open_id,
                User.is_deleted == False,  # noqa: E712
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_feishu_user_id(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                User.feishu_user_id == user_id,
                User.is_deleted == False,  # noqa: E712
            ),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        *,
        name: str,
        feishu_user_id: str | None = None,
        feishu_open_id: str | None = None,
        feishu_union_id: str | None = None,
        en_name: str | None = None,
        employee_no: str | None = None,
        email: str | None = None,
        enterprise_email: str | None = None,
        mobile: str | None = None,
        avatar_url: str | None = None,
        avatar_thumb: str | None = None,
        avatar_middle: str | None = None,
        avatar_big: str | None = None,
        tenant_key: str | None = None,
        department: str | None = None,
        position: str | None = None,
        feishu_department_ids: str | None = None,
        username: str | None = None,
        password_hash: str | None = None,
        must_change_password: bool = False,
        status: str = "active",
        auth_source: str = "feishu",
    ) -> User:
        user = User(
            name=name,
            username=username,
            password_hash=password_hash,
            must_change_password=must_change_password,
            status=status,
            auth_source=auth_source,
            feishu_user_id=feishu_user_id,
            feishu_open_id=feishu_open_id,
            feishu_union_id=feishu_union_id,
            en_name=en_name,
            employee_no=employee_no,
            email=email,
            enterprise_email=enterprise_email,
            mobile=mobile,
            avatar_url=avatar_url,
            avatar_thumb=avatar_thumb,
            avatar_middle=avatar_middle,
            avatar_big=avatar_big,
            tenant_key=tenant_key,
            department=department,
            position=position,
            feishu_department_ids=feishu_department_ids,
        )
        session.add(user)
        await session.flush()
        return user

    async def allocate_username(
        self,
        session: AsyncSession,
        *,
        prefix: str,
        max_attempts: int = 20,
    ) -> str:
        """分配默认用户名 `{prefix}{6 位自增号}`（如 YTH000001）。

        用 PG 序列 `identity.user_username_seq` 的 nextval 保证并发建号不撞号；
        若序列值与既有账号重合（例如历史上手工建过同前缀用户名），跳过再取下一个。
        """
        for _ in range(max_attempts):
            result = await session.execute(select(func.nextval("identity.user_username_seq")))
            candidate = f"{prefix}{int(result.scalar_one()):06d}"
            # 唯一约束含软删行，判重不能加 is_deleted 过滤
            existing = await session.execute(select(User.id).where(User.username == candidate).limit(1))
            if existing.scalar_one_or_none() is None:
                return candidate
        raise RuntimeError(f"无法分配唯一用户名（前缀 {prefix}），请检查 identity.user_username_seq 序列状态")

    async def list_users(
        self,
        session: AsyncSession,
        *,
        keyword: str | None = None,
        status: str | None = None,
        auth_source: str | None = None,
        unbound_only: bool = False,
        must_change_password: bool | None = None,
        exclude_user_ids: list[UUID] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[User], int]:
        base = select(User).where(User.is_deleted == False)  # noqa: E712
        count_stmt = (
            select(func.count())
            .select_from(User)
            .where(
                User.is_deleted == False  # noqa: E712
            )
        )

        # 对非超管隐藏超管账号（调用方传入超管 id 列表）
        if exclude_user_ids:
            base = base.where(User.id.not_in(exclude_user_ids))
            count_stmt = count_stmt.where(User.id.not_in(exclude_user_ids))

        if keyword:
            pattern = f"%{keyword}%"
            filter_expr = or_(
                User.name.ilike(pattern),
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.mobile.ilike(pattern),
                User.employee_no.ilike(pattern),
            )
            base = base.where(filter_expr)
            count_stmt = count_stmt.where(filter_expr)
        if status:
            base = base.where(User.status == status)
            count_stmt = count_stmt.where(User.status == status)
        if auth_source:
            base = base.where(User.auth_source == auth_source)
            count_stmt = count_stmt.where(User.auth_source == auth_source)
        if unbound_only:
            # 仅返回尚未绑定飞书身份的账号（供「绑定飞书」选择器使用）
            base = base.where(User.feishu_user_id.is_(None), User.feishu_open_id.is_(None))
            count_stmt = count_stmt.where(User.feishu_user_id.is_(None), User.feishu_open_id.is_(None))
        if must_change_password is not None:
            base = base.where(User.must_change_password == must_change_password)
            count_stmt = count_stmt.where(User.must_change_password == must_change_password)

        total = int((await session.execute(count_stmt)).scalar_one())
        result = await session.execute(base.order_by(User.created_at.desc()).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def get_roles_for_users(
        self,
        session: AsyncSession,
        user_ids: list[UUID],
    ) -> dict[UUID, list[str]]:
        """批量取用户的有效角色名（用户管理列表的「角色」列据此显示）。

        只统计「生效中」的授权（授权 status=active 且未软删）——禁用授权不算。
        """
        if not user_ids:
            return {}
        # 函数内导入：避免 identity ↔ permission 模块级循环依赖
        from app.platform.permission.models import GRANT_ACTIVE, Role, UserRoleGrant

        stmt = (
            select(UserRoleGrant.user_id, Role.name)
            .join(Role, Role.id == UserRoleGrant.role_id)
            .where(
                UserRoleGrant.user_id.in_(user_ids),
                UserRoleGrant.is_deleted == False,  # noqa: E712
                UserRoleGrant.status == GRANT_ACTIVE,
            )
            .order_by(Role.name)
        )
        rows = (await session.execute(stmt)).all()
        result: dict[UUID, list[str]] = {}
        for user_id, role_name in rows:
            result.setdefault(user_id, []).append(role_name)
        return result

    async def list_all(
        self,
        session: AsyncSession,
        *,
        department_id: str | None = None,
        keyword: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[User], int]:
        """分页查询所有用户，支持按部门/关键词筛选。"""
        base = select(User).where(User.is_deleted == False)  # noqa: E712

        if department_id:
            base = base.where(
                User.feishu_department_ids.contains(department_id),
            )
        if keyword:
            base = base.where(
                User.name.ilike(f"%{keyword}%"),
            )

        count_stmt = select(User.id).where(User.is_deleted == False)  # noqa: E712
        if department_id:
            count_stmt = count_stmt.where(
                User.feishu_department_ids.contains(department_id),
            )
        if keyword:
            count_stmt = count_stmt.where(
                User.name.ilike(f"%{keyword}%"),
            )
        total_result = await session.execute(count_stmt)
        total = len(total_result.scalars().all())

        stmt = base.order_by(User.name).offset(offset).limit(limit)
        result = await session.execute(stmt)
        users = list(result.scalars().all())
        return users, total


class DepartmentRepository:
    async def get_by_feishu_id(
        self,
        session: AsyncSession,
        feishu_dept_id: str,
    ) -> Department | None:
        result = await session.execute(
            select(Department).where(
                Department.feishu_department_id == feishu_dept_id,
            ),
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        session: AsyncSession,
        *,
        include_deleted: bool = False,
    ) -> list[Department]:
        stmt = select(Department).where(
            Department.is_deleted == False,  # noqa: E712
        )
        if not include_deleted:
            stmt = stmt.where(Department.status_is_deleted == False)  # noqa: E712
        stmt = stmt.order_by(Department.order, Department.name)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_children(
        self,
        session: AsyncSession,
        parent_id: str,
    ) -> list[Department]:
        stmt = (
            select(Department)
            .where(
                Department.parent_feishu_department_id == parent_id,
                Department.is_deleted == False,  # noqa: E712
                Department.status_is_deleted == False,  # noqa: E712
            )
            .order_by(Department.order, Department.name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


class LoginLogRepository:
    async def create(  # type: ignore[no-untyped-def]
        self,
        session: AsyncSession,
        *,
        user_id=None,
        user_name: str | None = None,
        login_type: str = "feishu_sso",
        status: str = "success",
        ip_address: str | None = None,
        user_agent: str | None = None,
        error_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        from app.platform.identity.models import LoginLog

        log = LoginLog(
            user_id=user_id,
            user_name=user_name,
            login_type=login_type,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
            extra=extra,
        )
        session.add(log)
        await session.flush()
        return log

    async def list_logs(
        self,
        session: AsyncSession,
        *,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        from app.platform.identity.models import LoginLog

        conditions = [LoginLog.is_deleted == False]  # noqa: E712
        if status:
            conditions.append(LoginLog.status == status)
        if keyword:
            conditions.append(LoginLog.user_name.ilike(f"%{keyword}%"))

        # 用 COUNT(*) 统计总数（原来把符合条件的全部 id 拉回内存再取长度，数据量增长后很慢）
        total = (await session.execute(select(func.count()).select_from(LoginLog).where(*conditions))).scalar_one()

        stmt = (
            select(LoginLog)
            .where(*conditions)
            .order_by(LoginLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all()), int(total)


class FeishuConfigRepository:
    async def get_active(self, session: AsyncSession) -> FeishuConfig | None:
        result = await session.execute(
            select(FeishuConfig)
            .where(
                FeishuConfig.is_deleted == False,  # noqa: E712
                FeishuConfig.is_active.is_(True),
            )
            .order_by(FeishuConfig.updated_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_latest(self, session: AsyncSession) -> FeishuConfig | None:
        result = await session.execute(
            select(FeishuConfig)
            .where(FeishuConfig.is_deleted == False)  # noqa: E712
            .order_by(FeishuConfig.updated_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_by_name_including_deleted(self, session: AsyncSession, config_name: str) -> FeishuConfig | None:
        result = await session.execute(
            select(FeishuConfig).where(FeishuConfig.config_name == config_name).order_by(FeishuConfig.updated_at.desc())
        )
        return result.scalar_one_or_none()

    async def save(self, session: AsyncSession, config: FeishuConfig) -> FeishuConfig:
        session.add(config)
        await session.flush()
        return config


class FeishuCardActionRepository:
    async def create(  # type: ignore[no-untyped-def]
        self,
        session: AsyncSession,
        *,
        message_id: str | None,
        card_id: str | None,
        local_user_id: UUID | None,
        recipient_open_id: str | None,
        business_ref: dict[str, Any] | None,
        action_key: str,
        action_label: str,
        expires_at,
    ) -> FeishuCardAction:
        action = FeishuCardAction(
            message_id=message_id,
            card_id=card_id,
            local_user_id=local_user_id,
            recipient_open_id=recipient_open_id,
            business_ref=business_ref,
            action_key=action_key,
            action_label=action_label,
            expires_at=expires_at,
        )
        session.add(action)
        await session.flush()
        return action

    async def get_pending_by_id(self, session: AsyncSession, action_id: UUID | str) -> FeishuCardAction | None:
        if isinstance(action_id, str):
            try:
                action_id = UUID(action_id)
            except ValueError:
                return None
        result = await session.execute(
            select(FeishuCardAction).where(
                FeishuCardAction.id == action_id,
                FeishuCardAction.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def set_message_id_for_card(
        self,
        session: AsyncSession,
        *,
        card_id: str,
        message_id: str | None,
    ) -> None:
        if not message_id:
            return
        result = await session.execute(
            select(FeishuCardAction).where(
                FeishuCardAction.card_id == card_id,
                FeishuCardAction.is_deleted == False,  # noqa: E712
            )
        )
        for action in result.scalars().all():
            action.message_id = message_id
        await session.flush()
